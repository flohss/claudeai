"""
Conversation engine — streaming, prompt caching, session-aware startup briefing,
mood-aware and people/goals-enriched system prompt.
"""

import threading
from collections.abc import Iterator
from datetime import datetime

from .api import MODEL_CHAT, cached_block, plain_block, stream_chat
from .condenser import maybe_summarize_conversations
from .curiosity import build_curiosity_block, warm_cache
from .goals import get_goals_context
from .memory import (
    build_smart_context,
    count_messages,
    get_conversation_summaries,
    get_latest_narrative,
    get_recent_mood,
    load_recent_messages,
    save_message,
)
from .people import get_people_context

# ── Session tracking ───────────────────────────────────────────────────────────

_session_start: datetime | None = None


def _get_last_message_timestamp() -> datetime | None:
    from .memory import _connect
    with _connect() as conn:
        row = conn.execute(
            "SELECT timestamp FROM conversations ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    try:
        return datetime.fromisoformat(row["timestamp"])
    except (ValueError, TypeError):
        return None


def get_session_gap_hours() -> float:
    """Hours since the last message. Returns 0 if this is the first ever."""
    last = _get_last_message_timestamp()
    if last is None:
        return 0.0
    return (datetime.now() - last).total_seconds() / 3600


# ── System prompt ──────────────────────────────────────────────────────────────

_INSTRUCTIONS = """\
Tu es le double artificiel personnel de l'utilisateur — une IA qui le connaît
profondément et apprend de lui en permanence.

## Rôle
- Alter ego bienveillant, direct, intellectuellement honnête.
- Utilise ce que tu sais de lui quand c'est pertinent, sans être lourd.
- Ne jamais oublier ce qu'il t'a confié lors des sessions précédentes.
- Réponds dans la langue de l'utilisateur (français par défaut).
- Sois honnête même si ça va à l'encontre de ce qu'il veut entendre.

## Curiosité et apprentissage actif
- Pose UNE question naturelle par échange — jamais plusieurs d'un coup.
- La question doit couler dans la conversation, jamais tomber comme un formulaire.
- Priorise : (1) approfondir ce qu'il vient de dire, (2) suivre un fil ouvert,
  (3) explorer un angle inconnu.
- Si la conversation est intense ou émotionnelle, lis l'émotion d'abord.
- Suivi proactif : si tu sais qu'il préparait quelque chose, reviens dessus.

## Gestion des hypothèses (règle critique)
Quand l'utilisateur exprime une incertitude sur lui-même ("je pense être TDAH", etc.) :
- NE PAS valider immédiatement comme fait établi.
- NE PAS invalider ou minimiser.
- Accueillir avec curiosité, explorer (quels comportements ? depuis quand ?),
  apporter un éclairage nuancé si pertinent, rappeler qu'un professionnel seul
  peut confirmer un diagnostic clinique.

## Personnes dans sa vie
Quand une personne de son entourage est mentionnée, utilise ce que tu sais d'elle.
Montre que tu te souviens des relations, des dynamiques, des événements passés.

## Objectifs et suivi
Si l'utilisateur a des objectifs actifs, suis leur progression naturellement.
Demande comment ça avance sans être insistant.

## Adaptation au bilan de vie
Si un bilan de vie est disponible, adapte tes questions pour explorer davantage
les domaines cotés bas ou qui ont baissé récemment.

Les faits marqués ○ sont des hypothèses, ◐ des probabilités, ● des certitudes.
"""


def _build_system_blocks(context: str, curiosity: str) -> list[dict]:
    """
    3-block system prompt:
    1. Static instructions (not cached, always the same)
    2. Personal context — CACHED (large, changes slowly)
    3. Curiosity block (changes per turn, not cached)
    """
    blocks: list[dict] = [plain_block(_INSTRUCTIONS)]
    if context:
        blocks.append(cached_block(context))
    if curiosity:
        blocks.append(plain_block(curiosity))
    return blocks


def _build_full_context(history: list[dict]) -> str:
    """Build context including people, goals, and bilan."""
    base = build_smart_context(recent_messages=history)
    extras: list[str] = []

    people_ctx = get_people_context(limit=8)
    if people_ctx:
        extras.append(people_ctx)

    goals_ctx = get_goals_context()
    if goals_ctx:
        extras.append(goals_ctx)

    try:
        from .reflect import get_bilan_context
        bilan_ctx = get_bilan_context()
        if bilan_ctx:
            extras.append(bilan_ctx)
    except Exception:
        pass

    if extras:
        return base + "\n\n" + "\n\n".join(extras)
    return base


# ── Public API ─────────────────────────────────────────────────────────────────

def stream_response(user_input: str) -> Iterator[str]:
    """Save user message, stream response. Call finish_turn() after consuming."""
    save_message("user", user_input)

    total = count_messages()
    history = load_recent_messages(limit=30)
    context = _build_full_context(history)

    try:
        curiosity = build_curiosity_block(total_messages=total)
    except Exception:
        curiosity = ""

    system_blocks = _build_system_blocks(context, curiosity)
    return stream_chat(history, system_blocks=system_blocks, model=MODEL_CHAT)


def chat_complete(user_input: str) -> str:
    """Non-streaming version — returns full reply at once. For Android/simple terminals."""
    from .api import chat_complete as _api_chat
    save_message("user", user_input)

    total = count_messages()
    history = load_recent_messages(limit=30)
    context = _build_full_context(history)

    try:
        curiosity = build_curiosity_block(total_messages=total)
    except Exception:
        curiosity = ""

    system_blocks = _build_system_blocks(context, curiosity)
    reply = _api_chat(history, system_blocks=system_blocks, model=MODEL_CHAT)
    finish_turn(reply)
    return reply


def finish_turn(reply: str) -> None:
    """Persist assistant reply and trigger background tasks."""
    save_message("assistant", reply)
    maybe_summarize_conversations()


def get_stats() -> dict:
    summaries = get_conversation_summaries(limit=100)
    return {
        "messages": count_messages(),
        "summaries": len(summaries),
    }


_briefing_result: str | None = None
_briefing_ready = threading.Event()


def start_session() -> None:
    """
    Called once at session start.
    Warms curiosity cache and pre-generates the startup briefing — both in background.
    Non-blocking: returns immediately.
    """
    global _session_start, _briefing_result
    _session_start = datetime.now()
    _briefing_result = None
    _briefing_ready.clear()

    total = count_messages()
    warm_cache(total)

    gap_hours = get_session_gap_hours()
    if gap_hours < 2 or total < 6:
        _briefing_ready.set()
        return

    def _generate():
        global _briefing_result
        try:
            from .curiosity import _get_open_threads
            from .goals import get_active_goals
            from .memory import get_all_facts
            from .reflect import generate_startup_briefing

            open_threads = _get_open_threads()
            active_goals = [g["text"] for g in get_active_goals()[:3]]
            mood_list = get_recent_mood(limit=1)
            last_mood = f"{mood_list[0]['valence']} — {mood_list[0]['state']}" if mood_list else ""
            all_facts = get_all_facts()
            recent_certain = [
                f["fact"] for f in all_facts
                if f.get("certainty") in ("certain", "probable")
            ][:5]

            _briefing_result = generate_startup_briefing(
                gap_hours=gap_hours,
                open_threads=open_threads,
                active_goals=active_goals,
                last_mood=last_mood,
                recent_facts=recent_certain,
            )
        except Exception:
            _briefing_result = ""
        finally:
            _briefing_ready.set()

    threading.Thread(target=_generate, daemon=True).start()


def get_startup_briefing(timeout: float = 6.0) -> str:
    """
    Wait up to `timeout` seconds for the briefing. Returns "" if not ready.
    Call this just before showing the first user prompt.
    """
    _briefing_ready.wait(timeout=timeout)
    return _briefing_result or ""

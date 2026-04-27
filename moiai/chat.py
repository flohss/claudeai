"""
Conversation engine — streaming responses, prompt caching for personal context,
mood-aware system prompt, pre-cached curiosity block.
"""

from collections.abc import Iterator

from .api import MODEL_CHAT, cached_block, plain_block, stream_chat
from .condenser import maybe_summarize_conversations
from .curiosity import build_curiosity_block, warm_cache
from .memory import (
    build_smart_context,
    count_messages,
    get_conversation_summaries,
    load_recent_messages,
    save_message,
)

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
- Priorise : (1) approfondir ce qu'il vient de dire, (2) suivre un fil ouvert
  de sessions précédentes, (3) explorer un angle inconnu.
- Si la conversation est intense ou émotionnelle, lis l'émotion d'abord.
- Suivi proactif : si tu sais qu'il préparait quelque chose ou traversait une période
  difficile, reviens dessus spontanément — c'est ce qui te différencie d'un chatbot.

## Gestion des hypothèses (règle critique)
Quand l'utilisateur exprime une incertitude sur lui-même ("je pense être TDAH",
"j'ai peut-être de l'anxiété", etc.) :
- NE PAS valider immédiatement comme fait établi.
- NE PAS invalider ou minimiser.
- Accueillir avec curiosité, explorer (quels comportements ? depuis quand ?),
  apporter un éclairage nuancé si pertinent, rappeler qu'un professionnel seul
  peut confirmer un diagnostic clinique.
- Mémoriser comme hypothèse, pas comme certitude.

## Humeur et ton
Les faits marqués ○ sont des hypothèses, ◐ des probabilités, ● des certitudes.
Adapte ton ton à l'humeur détectée : si l'utilisateur est stressé ou négatif,
sois plus doux et attentif avant d'être analytique.
"""


def _build_system_blocks(context: str, curiosity: str) -> list[dict]:
    """
    Build system as list of content blocks for prompt caching.
    - Instructions: static, not cached (short, always the same)
    - Context: large personal knowledge → CACHED (changes slowly)
    - Curiosity: changes every turn → not cached
    """
    blocks: list[dict] = [plain_block(_INSTRUCTIONS)]

    if context:
        # Cache the personal context — it's large and reused across turns
        blocks.append(cached_block(context))

    if curiosity:
        blocks.append(plain_block(curiosity))

    return blocks


# ── Public API ─────────────────────────────────────────────────────────────────

def stream_response(user_input: str) -> Iterator[str]:
    """
    Save user message, stream assistant response token by token.
    Caller must call finish_turn() after consuming the stream.
    Returns an iterator of text chunks.
    """
    save_message("user", user_input)

    total = count_messages()
    history = load_recent_messages(limit=30)
    context = build_smart_context(recent_messages=history)

    try:
        curiosity = build_curiosity_block(total_messages=total)
    except Exception:
        curiosity = ""

    system_blocks = _build_system_blocks(context, curiosity)

    return stream_chat(history, system_blocks=system_blocks, model=MODEL_CHAT)


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


def start_session() -> None:
    """Warm curiosity cache at session start so first turn has no latency."""
    total = count_messages()
    warm_cache(total)

"""
Curiosity engine — detects knowledge gaps and open threads, generates targeted
questions using Haiku, and caches them for the next turn to avoid latency.
"""

import json
import re
import threading

from .api import MODEL_FAST, complete
from .memory import (
    get_all_facts,
    get_conversation_summaries,
    get_profile,
)

# ── Config ─────────────────────────────────────────────────────────────────────

_TARGET_CATEGORIES = [
    "identité", "famille", "relations", "travail", "éducation", "localisation",
    "santé", "psychologie", "valeurs", "loisirs", "habitudes", "projets",
]
_MIN_FACTS_PER_CAT = 3

# ── Turn-level cache ───────────────────────────────────────────────────────────
# After each turn, we pre-generate questions for the NEXT turn in background.
# _cached_block is consumed and replaced on each call to build_curiosity_block().

_cache_lock = threading.Lock()
_cached_block: str | None = None


def _set_cache(block: str) -> None:
    global _cached_block
    with _cache_lock:
        _cached_block = block


def _pop_cache() -> str | None:
    global _cached_block
    with _cache_lock:
        val = _cached_block
        _cached_block = None
    return val


# ── Open-thread detection ──────────────────────────────────────────────────────

# Regex covers base forms + common inflections in French
_OPEN_PATTERNS = re.compile(
    r"\b(prépare?|essaie?|espère?|attend|cherche?|commence?|veut|voudrai[st]|"
    r"aimerais?|envisage?|postule?|candidature|entretien|interview|"
    r"déménage?|déménagement|prévu|bientôt|en cours|en train|travaille\s+sur|"
    r"objectif|projet|lance?|démarre?|crée?|démissionne?|arrête?|reprend?)\b",
    re.IGNORECASE,
)


def _get_open_threads() -> list[str]:
    facts = get_all_facts()
    threads: list[str] = []
    for f in facts:
        if _OPEN_PATTERNS.search(f["fact"]) or f.get("certainty") == "hypothèse":
            threads.append(f["fact"])
    return threads[:6]


def _get_gaps() -> list[str]:
    facts = get_all_facts()
    covered: dict[str, int] = {}
    for f in facts:
        covered[f["category"]] = covered.get(f["category"], 0) + 1
    return [cat for cat in _TARGET_CATEGORIES if covered.get(cat, 0) < _MIN_FACTS_PER_CAT]


# ── Question generation ────────────────────────────────────────────────────────

_SYSTEM = "Tu génères des questions. Réponds uniquement en JSON valide (tableau de strings)."

_Q_PROMPT = """\
{instruction}

Contexte :
{context}

Règles :
- Questions courtes, naturelles, jamais intrusives.
- Pas un interrogatoire — une seule logique conversationnelle.
- Variété de ton : curiosité directe, anecdotique, hypothétique.
- Retourne UNIQUEMENT un tableau JSON de strings. Exemple : ["Question 1 ?", "Question 2 ?"]
"""


def _generate_questions(gaps: list[str], threads: list[str], is_first: bool) -> list[str]:
    profile = get_profile()
    summaries = get_conversation_summaries(limit=2)

    ctx_parts: list[str] = []
    if profile:
        ctx_parts.append("Profil connu : " + ", ".join(f"{k}={v}" for k, v in list(profile.items())[:8]))
    if summaries:
        ctx_parts.append("Sessions passées : " + " | ".join(summaries[:2]))
    if gaps:
        ctx_parts.append("Angles morts : " + ", ".join(gaps[:5]))
    if threads:
        ctx_parts.append("Fils ouverts : " + " | ".join(threads[:4]))

    if is_first:
        instruction = (
            "Première session. Génère 3 questions chaleureuses et ouvertes pour apprendre "
            "à connaître cette personne — qui elle est, ce qui l'anime, son contexte de vie."
        )
    else:
        instruction = (
            "Génère 2 à 3 questions ciblées. Priorité : (1) fils ouverts, "
            "(2) angles morts importants, (3) approfondissement du profil."
        )

    prompt = _Q_PROMPT.format(
        instruction=instruction,
        context="\n".join(ctx_parts) if ctx_parts else "Aucune info connue.",
    )

    raw = complete(prompt, system=_SYSTEM, model=MODEL_FAST, max_tokens=256)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        qs = json.loads(raw)
        return [q for q in qs if isinstance(q, str)][:3]
    except (json.JSONDecodeError, TypeError):
        return []


# ── Public API ─────────────────────────────────────────────────────────────────

_LIGHT = """
## Curiosité active
Tu connais déjà beaucoup cette personne. Reste attentif à ce qu'elle partage.
Si une ouverture naturelle se présente, approfondis.
"""


def build_curiosity_block(total_messages: int) -> str:
    """
    Return the curiosity block for the current turn (from cache if available),
    then pre-generate the next one in background.
    """
    # Try to use the cached block from the previous turn
    cached = _pop_cache()
    if cached is not None:
        _prefetch_next(total_messages)
        return cached

    # Cache miss — generate synchronously this turn
    block = _build_block(total_messages)
    _prefetch_next(total_messages)
    return block


def _build_block(total_messages: int) -> str:
    is_first = total_messages < 6
    gaps = _get_gaps()
    threads = _get_open_threads()

    if not is_first and not gaps and not threads:
        return _LIGHT

    try:
        questions = _generate_questions(gaps[:4], threads, is_first)
    except Exception:
        return _LIGHT

    if not questions:
        return _LIGHT

    lines = ["\n## Curiosité active — questions à explorer"]
    if is_first:
        lines.insert(0, "\n## Première session — mode découverte")
        lines.insert(1, "Tu ne connais pas encore cette personne. Sois chaleureux et curieux.")
        lines.insert(2, "Présente-toi brièvement et lance avec UNE de ces questions :")
        lines.insert(3, "")
    else:
        lines.append("Intègre naturellement UNE de ces questions si le contexte s'y prête.")
        lines.append("Ne les liste pas toutes, ne sois pas mécanique :")
    lines.append("")
    for q in questions:
        lines.append(f"- {q}")

    return "\n".join(lines)


def _prefetch_next(total_messages: int) -> None:
    """Pre-generate the curiosity block for the next turn in background."""
    def _run():
        try:
            block = _build_block(total_messages + 2)  # +2 = user + assistant saved
            _set_cache(block)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


def warm_cache(total_messages: int) -> None:
    """Explicitly warm the cache (call at session start)."""
    _prefetch_next(total_messages)

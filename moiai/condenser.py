"""
Memory condenser — uses Claude to compress all accumulated facts and profile
into a rich personal narrative, and to summarize old conversation chunks.
"""

import anthropic

from .memory import (
    get_all_facts,
    get_conversation_summaries,
    get_latest_narrative,
    get_profile,
    load_messages_for_summary,
    save_conversation_summary,
    save_narrative,
)

_client: anthropic.Anthropic | None = None

# Trigger auto-summarization when unsummarized messages exceed this count
AUTO_SUMMARIZE_THRESHOLD = 80


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


# ── Narrative condensation ─────────────────────────────────────────────────────

_NARRATIVE_PROMPT = """\
Tu es un psychologue et biographe. À partir des éléments ci-dessous — profil, \
faits mémorisés et ancienne narration — rédige une narration personnelle riche, \
fluide et dense sur cet individu.

La narration doit :
- Être à la 3e personne ("Il/Elle…" ou utiliser le prénom si connu)
- Couvrir : identité, personnalité, valeurs, relations, travail, loisirs, habitudes, projets, santé, histoire
- Faire ressortir les patterns de comportement, les contradictions, les forces
- Être dense en informations (pas de phrases creuses)
- Être rédigée en français, en prose (pas de bullet points)
- Faire entre 300 et 600 mots

Ne répète pas mot pour mot les faits, synthétise-les en portrait vivant.
"""

_NARRATIVE_UPDATE_INTRO = "\n\n---\nNarration précédente (à enrichir, pas à remplacer) :\n"


def condense_narrative() -> str:
    """Generate or update the condensed personal narrative. Returns the new text."""
    profile = get_profile()
    facts = get_all_facts()
    old_narrative = get_latest_narrative()

    # Build context
    parts: list[str] = []

    if profile:
        parts.append("## Profil\n" + "\n".join(f"- {k}: {v}" for k, v in profile.items()))

    if facts:
        by_cat: dict[str, list[str]] = {}
        for f in facts:
            by_cat.setdefault(f["category"], []).append(f["fact"])
        fact_lines = ["## Faits"]
        for cat, items in by_cat.items():
            fact_lines.append(f"### {cat}")
            fact_lines.extend(f"- {i}" for i in items)
        parts.append("\n".join(fact_lines))

    if not parts:
        return ""

    prompt = _NARRATIVE_PROMPT + "\n\n" + "\n\n".join(parts)
    if old_narrative:
        prompt += _NARRATIVE_UPDATE_INTRO + old_narrative

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system="Tu es un biographe expert. Rédige uniquement la narration demandée, sans commentaires.",
        messages=[{"role": "user", "content": prompt}],
    )

    narrative = response.content[0].text.strip()
    save_narrative(narrative)
    return narrative


# ── Conversation summarization ─────────────────────────────────────────────────

_SUMMARIZE_PROMPT = """\
Résume en 3 à 6 phrases concises les échanges ci-dessous. Capture :
- Les sujets principaux abordés
- Les informations importantes partagées par l'utilisateur
- L'état émotionnel ou les préoccupations de l'utilisateur si perceptibles
- Toute décision ou information clé à retenir

Réponds uniquement avec le résumé, sans introduction ni commentaire.

Échanges :
"""


def summarize_old_conversations(after_id: int = 0) -> str | None:
    """
    Summarize older conversation messages and mark them as summarized.
    Returns the summary text, or None if nothing to summarize.
    """
    messages = load_messages_for_summary(after_id=after_id, limit=60)
    if len(messages) < 10:
        return None

    text_lines = [f"{m['role'].capitalize()} : {m['content']}" for m in messages]
    prompt = _SUMMARIZE_PROMPT + "\n".join(text_lines)

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="Tu es un assistant de résumé. Réponds uniquement avec le résumé.",
        messages=[{"role": "user", "content": prompt}],
    )

    summary = response.content[0].text.strip()
    last_id = messages[-1]["id"]
    save_conversation_summary(summary, last_id)
    return summary


def maybe_summarize_conversations() -> bool:
    """Auto-trigger summarization if conversation has grown long. Returns True if triggered."""
    from .memory import count_unsummarized_messages, get_last_message_id
    count = count_unsummarized_messages()
    if count >= AUTO_SUMMARIZE_THRESHOLD:
        # Keep last 20 messages unsummarized (active context)
        last_id = get_last_message_id()
        cutoff = last_id - 20
        if cutoff > 0:
            summarize_old_conversations(after_id=0)
            return True
    return False

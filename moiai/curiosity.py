"""
Curiosity engine — detects knowledge gaps and open threads, then generates
targeted questions for the AI to ask the user in conversation.
"""

import json

import anthropic

from .memory import get_all_facts, get_conversation_summaries, get_latest_narrative, get_profile

_client: anthropic.Anthropic | None = None

# Categories we want to eventually know about every user
_TARGET_CATEGORIES = [
    "identité",
    "famille",
    "relations",
    "travail",
    "éducation",
    "localisation",
    "santé",
    "psychologie",
    "valeurs",
    "croyances",
    "loisirs",
    "habitudes",
    "projets",
    "finances",
    "alimentation",
]

# Minimum facts per category before we stop actively seeking more
_MIN_FACTS_PER_CAT = 2


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _get_covered_categories() -> dict[str, int]:
    """Return {category: fact_count} for all known facts."""
    facts = get_all_facts()
    counts: dict[str, int] = {}
    for f in facts:
        cat = f["category"].lower()
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def _get_open_threads() -> list[str]:
    """
    Return facts that suggest an unresolved situation worth following up on.
    Heuristics: contains verbs like "prépare", "essaie", "espère", "attend",
    "cherche", "commence", "veut", "pense à" — or is recent and probable/hypothèse.
    """
    facts = get_all_facts()
    open_keywords = {
        "prépare", "essaie", "espère", "attend", "cherche", "commence",
        "veut", "pense à", "prévu", "bientôt", "projet", "objectif",
        "voudrait", "aimerait", "envisage", "en cours", "en train",
        "travaille sur", "postule", "candidature", "entretien", "interview",
        "déménage", "déménagement", "relation", "rencontre",
    }
    threads: list[str] = []
    for f in facts:
        text = f["fact"].lower()
        if any(kw in text for kw in open_keywords):
            threads.append(f["fact"])
        elif f.get("certainty") == "hypothèse":
            threads.append(f["fact"])
    return threads[:5]


def _generate_questions(gaps: list[str], threads: list[str], is_first_session: bool) -> list[str]:
    """Call Claude to generate 2-3 natural, targeted questions."""
    profile = get_profile()
    summaries = get_conversation_summaries(limit=2)

    context_parts: list[str] = []

    if profile:
        context_parts.append("Profil connu : " + ", ".join(f"{k}={v}" for k, v in profile.items()))

    if summaries:
        context_parts.append("Résumés récents : " + " | ".join(summaries))

    if gaps:
        context_parts.append("Angles morts (pas encore explorés) : " + ", ".join(gaps))

    if threads:
        context_parts.append("Fils ouverts à suivre : " + " | ".join(threads))

    context = "\n".join(context_parts) if context_parts else "Aucune information connue."

    if is_first_session:
        instruction = (
            "C'est la toute première session. Génère 3 questions chaleureuses et ouvertes "
            "pour apprendre à connaître cette personne — qui elle est, ce qu'elle fait, "
            "ce qui l'anime. Questions naturelles, pas un formulaire."
        )
    else:
        instruction = (
            "Génère 2 à 3 questions naturelles et ciblées que l'IA devrait poser "
            "pour mieux connaître cette personne. Priorise : (1) les fils ouverts à suivre, "
            "(2) les angles morts importants. Questions courtes, conversationnelles, jamais intrusives. "
            "Variété de ton : curiosité sincère, pas interrogatoire."
        )

    prompt = f"""{instruction}

Contexte :
{context}

Retourne UNIQUEMENT un tableau JSON de strings (les questions), sans aucun autre texte.
Exemple : ["Question 1 ?", "Question 2 ?"]
"""

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="Tu génères des questions. Réponds uniquement en JSON valide.",
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        questions = json.loads(raw)
        return [q for q in questions if isinstance(q, str)][:3]
    except (json.JSONDecodeError, TypeError):
        return []


def build_curiosity_block(total_messages: int) -> str:
    """
    Build the curiosity section injected into the system prompt.
    Returns an empty string if there's nothing useful to suggest.
    """
    is_first_session = total_messages < 6
    covered = _get_covered_categories()
    threads = _get_open_threads()

    # Gaps: important categories with fewer than minimum facts
    gaps = [
        cat for cat in _TARGET_CATEGORIES
        if covered.get(cat, 0) < _MIN_FACTS_PER_CAT
    ]

    # If we know a lot and have no threads, don't force questions every turn
    if not is_first_session and not gaps and not threads:
        return _LIGHT_CURIOSITY

    try:
        questions = _generate_questions(gaps[:4], threads, is_first_session)
    except Exception:
        questions = []

    if not questions:
        return _LIGHT_CURIOSITY

    lines = [
        "\n## Curiosité active — questions à explorer dans cet échange",
        "Intègre naturellement UNE de ces questions dans ta réponse si le contexte s'y prête.",
        "Ne les liste pas toutes, ne sois pas mécanique. Choisis celle qui coule le mieux :",
        "",
    ]
    for q in questions:
        lines.append(f"- {q}")

    if is_first_session:
        lines.insert(0, "\n## Première session — mode découverte")
        lines.insert(1, "Tu ne connais pas encore cette personne. Sois chaleureux, curieux, accueillant.")
        lines.insert(2, "Présente-toi brièvement et lance la conversation avec une des questions ci-dessous.")
        lines.insert(3, "")

    return "\n".join(lines)


_LIGHT_CURIOSITY = """
## Curiosité active
Tu connais déjà beaucoup cette personne. Reste attentif à ce qu'elle partage spontanément.
Si une ouverture naturelle se présente, approfondis. Sinon, suis le fil de la conversation.
"""

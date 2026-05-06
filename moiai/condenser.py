"""
Memory condenser — compresses facts into a narrative and old conversations
into summaries, using retry-wrapped API calls.
"""

from .api import MODEL_FAST, MODEL_SMART, complete
from .settings import get as _cfg
from .memory import (
    count_unsummarized_messages,
    get_all_facts,
    get_last_message_id,
    get_latest_narrative,
    get_profile,
    load_messages_for_summary,
    save_conversation_summary,
    save_narrative,
)

AUTO_SUMMARIZE_THRESHOLD = 80  # fallback only — runtime value read from settings

_NARRATIVE_SYSTEM = "Tu es un biographe expert. Rédige uniquement la narration demandée, sans commentaires."

_NARRATIVE_PROMPT = """\
Tu es un psychologue et biographe. À partir des éléments ci-dessous — profil,
faits mémorisés et ancienne narration — rédige une narration personnelle riche,
fluide et dense sur cet individu.

La narration doit :
- Être à la 3e personne ("Il/Elle…" ou utiliser le prénom si connu)
- Couvrir : identité, personnalité, valeurs, relations, travail, loisirs, habitudes, projets, santé
- Faire ressortir les patterns de comportement, les contradictions, les forces
- Être dense en informations (pas de phrases creuses)
- Être rédigée en français, en prose (pas de bullet points)
- Faire entre 300 et 600 mots
- Intégrer les hypothèses (○) avec des formulations prudentes ("semble", "aurait tendance à")

Ne répète pas mot pour mot les faits — synthétise-les en portrait vivant.
"""

_NARRATIVE_UPDATE_INTRO = "\n\n---\nNarration précédente (à enrichir, pas à remplacer) :\n"

_UNIFIED_SYSTEM = "Tu es un biographe expert. Rédige uniquement le document demandé, sans commentaires."

_UNIFIED_PROMPT = """\
Tu es un psychologue et biographe. Génère un document de connaissance complet et cohérent
sur cet individu, à partir de toutes les données ci-dessous.

Ce document sera utilisé comme contexte unique pour une IA personnelle — il doit être
dense, précis, et couvrir tous les aspects de la vie de la personne.

Structure obligatoire (prose, pas de bullet points) :

**Identité & parcours** — qui il/elle est, d'où il/elle vient, formation, parcours pro

**Personnalité & valeurs** — traits dominants, contradictions, forces, patterns comportementaux

**Relations & entourage** — famille proche, amis, relations importantes, dynamiques clés

**Vie quotidienne & habitudes** — travail, loisirs, santé, alimentation, rythme de vie

**Projets & objectifs** — ce qu'il/elle poursuit en ce moment, aspirations

**État actuel** — préoccupations récentes, humeur générale, sujets en cours

Règles :
- 600 à 900 mots
- Prose fluide, pas de listes
- Intégrer les hypothèses avec "semble", "aurait tendance à"
- Utiliser le prénom si connu
- Ne pas inventer — ne synthétiser que ce qui est dans les données
"""

_SUMMARIZE_SYSTEM = "Tu es un assistant de résumé. Réponds uniquement avec le résumé."

_SUMMARIZE_PROMPT = """\
Résume en 3 à 6 phrases concises les échanges ci-dessous. Capture :
- Les sujets principaux abordés
- Les informations importantes partagées par l'utilisateur
- L'état émotionnel ou les préoccupations de l'utilisateur si perceptibles
- Toute décision ou information clé à retenir

Réponds uniquement avec le résumé, sans introduction ni commentaire.

Échanges :
"""


def _build_facts_block(facts: list[dict]) -> str:
    active = [f for f in facts if f.get("certainty") != "réfuté"]
    by_cat: dict[str, list[str]] = {}
    for f in active:
        badge = "○" if f.get("certainty") == "hypothèse" else "●"
        by_cat.setdefault(f["category"], []).append(f"{badge} {f['fact']}")
    lines = ["## Faits (● certain, ○ hypothèse)"]
    for cat, items in by_cat.items():
        lines.append(f"### {cat}")
        lines.extend(f"- {i}" for i in items)
    return "\n".join(lines)


def condense_narrative() -> str:
    """Generate or update the condensed personal narrative. Returns the new text."""
    profile = get_profile()
    facts = get_all_facts()
    old_narrative = get_latest_narrative()

    parts: list[str] = []
    if profile:
        parts.append("## Profil\n" + "\n".join(f"- {k}: {v}" for k, v in profile.items()))
    if facts:
        parts.append(_build_facts_block(facts))
    if not parts:
        return ""

    prompt = _NARRATIVE_PROMPT + "\n\n" + "\n\n".join(parts)
    if old_narrative:
        prompt += _NARRATIVE_UPDATE_INTRO + old_narrative

    narrative = complete(prompt, system=_NARRATIVE_SYSTEM, model=MODEL_SMART, max_tokens=2048)
    narrative = narrative.strip()
    save_narrative(narrative)
    return narrative


def condense_unified() -> str:
    """
    Generate a single unified context document merging facts, profile, people,
    goals, and conversation summaries. Used when contexte_unifié=1.
    """
    from .goals import get_goals_context
    from .people import get_all_people
    from .memory import get_conversation_summaries

    profile = get_profile()
    facts = get_all_facts()
    old_narrative = get_latest_narrative()

    parts: list[str] = []

    if profile:
        parts.append("## Profil\n" + "\n".join(f"- {k}: {v}" for k, v in profile.items()))

    if facts:
        parts.append(_build_facts_block(facts))

    people = get_all_people()
    if people:
        lines = ["## Personnes dans sa vie"]
        for p in people[:30]:
            rel = f" ({p['relation']})" if p.get("relation") else ""
            note = f" — {p['notes'][:300]}" if p.get("notes") else ""
            lines.append(f"- {p['name']}{rel}{note}")
        parts.append("\n".join(lines))

    goals_ctx = get_goals_context()
    if goals_ctx:
        parts.append(goals_ctx)

    summaries = get_conversation_summaries(limit=5)
    if summaries:
        lines = ["## Conversations récentes (résumés)"]
        lines.extend(f"- {s}" for s in summaries)
        parts.append("\n".join(lines))

    if old_narrative:
        parts.append("## Narration précédente (à enrichir)\n" + old_narrative)

    if not parts:
        return ""

    prompt = _UNIFIED_PROMPT + "\n\n" + "\n\n".join(parts)
    narrative = complete(prompt, system=_UNIFIED_SYSTEM, model=MODEL_SMART, max_tokens=3000)
    narrative = narrative.strip()
    save_narrative(narrative)
    return narrative


def summarize_old_conversations(after_id: int = 0) -> str | None:
    messages = load_messages_for_summary(after_id=after_id, limit=60)
    if len(messages) < 10:
        return None

    text_lines = [f"{m['role'].capitalize()} : {m['content']}" for m in messages]
    prompt = _SUMMARIZE_PROMPT + "\n".join(text_lines)

    summary = complete(prompt, system=_SUMMARIZE_SYSTEM, model=MODEL_FAST, max_tokens=512)
    summary = summary.strip()
    last_id = messages[-1]["id"]
    save_conversation_summary(summary, last_id)
    return summary


def maybe_summarize_conversations() -> bool:
    """Auto-trigger summarization when history grows long. Returns True if triggered."""
    threshold = _cfg("seuil_auto_résumé")
    if threshold == 0:
        return False
    count = count_unsummarized_messages()
    if count >= threshold:
        last_id = get_last_message_id()
        cutoff = last_id - 20
        if cutoff > 0:
            summarize_old_conversations(after_id=0)
            return True
    return False

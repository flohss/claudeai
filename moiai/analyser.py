"""
A posteriori fact analyser — audits the full memory for quality, coherence,
patterns, and gaps. Uses Sonnet for deep analysis.
"""

from .api import MODEL_CHAT, complete
from .memory import CERTAINTY_BADGE, get_all_facts, get_profile

_SYSTEM = "Tu es un expert en analyse de mémoire biographique. Réponds en markdown structuré, français direct."

_PROMPT = """\
Tu analyses la mémoire personnelle d'un utilisateur stockée dans une base de faits.
Fais un audit complet, honnête, et actionnable.

PROFIL :
{profile}

FAITS MÉMORISÉS ({fact_count} faits) :
{facts_block}

Produis une analyse structurée avec ces sections EXACTES (en markdown) :

## Vue d'ensemble
Bref état des lieux : répartition par domaine, richesse globale, qualité générale (note /10).

## Thèmes dominants
Les 3-5 patterns ou valeurs qui ressortent implicitement à travers plusieurs faits.
Sois précis : cite des faits spécifiques pour illustrer chaque pattern.

## Incohérences & tensions
Contradictions subtiles ou tensions entre faits (pas seulement les paires évidentes).
Format : [Fait #X] vs [Fait #Y] — explication.
Si aucune : dire "Aucune incohérence détectée."

## Lacunes importantes
Domaines de vie sous-représentés ou absents. Qu'est-ce qu'on ne sait pas encore
et qui serait important pour construire une mémoire complète ?

## Faits à enrichir
Faits trop vagues, datés, ou incomplets qui mériteraient d'être précisés.
Format : Fait #ID ("texte court…") → ce qui manque / ce qu'il faudrait clarifier.
Maximum 5 faits.

## Questions prioritaires
Les 4 questions les plus importantes à poser pour améliorer la qualité de cette mémoire.
Questions concrètes, personnelles, ouvertes.

Sois direct et précis. Évite les généralités. Mentionne les IDs des faits quand pertinent.
"""


def analyse_facts() -> str:
    """Run a full audit of the memory and return a markdown report."""
    facts = get_all_facts()
    profile = get_profile()

    if not facts:
        return "Aucun fait mémorisé. Commence à parler pour construire ta mémoire."

    # Format profile
    profile_lines = "\n".join(f"- {k} : {v}" for k, v in profile.items()) or "Aucun profil."

    # Format facts with ID, category, certainty badge, text
    fact_lines = []
    for f in facts:
        badge = CERTAINTY_BADGE.get(f.get("certainty", "certain"), "●")
        fact_lines.append(
            f"[#{f['id']} · {f['category']} · {badge}] {f['fact']}"
        )
    facts_block = "\n".join(fact_lines)

    prompt = _PROMPT.format(
        profile=profile_lines,
        fact_count=len(facts),
        facts_block=facts_block,
    )

    return complete(prompt, system=_SYSTEM, model=MODEL_CHAT, max_tokens=1800)

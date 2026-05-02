"""
Fact merger — detects redundant/overlapping facts and proposes consolidated versions.
Uses Haiku for detection (cheap), returns merge candidates for interactive validation.
"""

import json

from .api import MODEL_FAST, complete
from .memory import CERTAINTY_BADGE

_SYSTEM = "Tu es un extracteur JSON silencieux. Réponds uniquement en JSON valide."

_PROMPT = """\
Voici une liste de faits mémorisés sur un utilisateur. Identifie les groupes de faits
qui se chevauchent, se répètent ou se complètent et pourraient être fusionnés en un seul
fait plus riche et précis.

FAITS :
{facts_block}

Retourne UNIQUEMENT ce JSON (tableau, potentiellement vide) :
[
  {{
    "ids": [12, 34],
    "merged": "formulation condensée qui garde toute l'information",
    "category": "catégorie_la_plus_pertinente",
    "reason": "explication courte en 10 mots max"
  }}
]

Règles strictes :
- Propose UNIQUEMENT des fusions où l'information se recoupe vraiment (même sujet, même période).
- Ne fusionne PAS des faits simplement parce qu'ils sont dans la même catégorie.
- Le texte "merged" doit être une phrase naturelle, complète, sans perte d'information.
- 2 à 4 faits par groupe maximum.
- Maximum 8 suggestions au total.
- Si aucune fusion évidente : retourner [].
- Aucun texte hors du JSON.
"""


def _parse_json(raw: str) -> list:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def suggest_merges(facts: list[dict]) -> list[dict]:
    """
    Analyse all active facts and return merge candidates.
    Each candidate: {ids: [...], merged: str, category: str, reason: str}
    """
    active = [f for f in facts if f.get("certainty") != "réfuté"]
    if len(active) < 2:
        return []

    fact_lines = []
    for f in active:
        badge = CERTAINTY_BADGE.get(f.get("certainty", "certain"), "●")
        fact_lines.append(f"#{f['id']} [{f['category']}] {badge} {f['fact']}")

    prompt = _PROMPT.format(facts_block="\n".join(fact_lines))
    raw = complete(prompt, system=_SYSTEM, model=MODEL_FAST, max_tokens=1024)
    candidates = _parse_json(raw)

    # Validate structure
    valid = []
    seen_ids: set[int] = set()
    for c in candidates:
        ids = c.get("ids", [])
        merged = (c.get("merged") or "").strip()
        category = (c.get("category") or "autre").strip()
        if not ids or not merged or len(ids) < 2:
            continue
        # Ensure all IDs exist in active facts and haven't been used in another group
        active_ids = {f["id"] for f in active}
        if not all(i in active_ids for i in ids):
            continue
        if any(i in seen_ids for i in ids):
            continue
        seen_ids.update(ids)
        valid.append({"ids": ids, "merged": merged, "category": category,
                      "reason": c.get("reason", "")})

    return valid

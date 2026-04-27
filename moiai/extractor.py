"""
Profile extraction engine — after each exchange, ask Claude to pull personal facts
from the conversation and merge them into persistent memory.
"""

import json
import anthropic

from .memory import add_facts, update_profile

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


_EXTRACTION_PROMPT = """\
Tu es un moteur d'extraction silencieux. Analyse l'échange ci-dessous et extrais \
toutes les informations personnelles explicites ou implicites sur l'utilisateur.

Retourne UNIQUEMENT un objet JSON valide avec cette structure exacte :
{
  "profile_updates": {
    "clé": "valeur"
  },
  "facts": [
    {"category": "catégorie", "fact": "fait précis en une phrase"}
  ]
}

Catégories possibles (non exhaustif) : identité, famille, travail, santé, loisirs, \
valeurs, habitudes, projets, finances, localisation, relations, éducation, croyances.

Règles :
- N'invente rien, extrais uniquement ce qui est dit.
- profile_updates = informations stables (nom, âge, ville, profession…).
- facts = tout fait utile à mémoriser, même ponctuel.
- Si rien à extraire, retourne {"profile_updates": {}, "facts": []}.
- Aucun texte hors du JSON.

Échange à analyser :
"""


def extract_and_store(user_msg: str, assistant_msg: str) -> int:
    """Extract personal info from one exchange and persist it. Returns fact count."""
    exchange = f"Utilisateur : {user_msg}\nAssistant : {assistant_msg}"

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="Tu es un extracteur JSON silencieux. Réponds uniquement en JSON valide.",
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT + exchange}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    for key, value in data.get("profile_updates", {}).items():
        if key and value:
            update_profile(str(key), str(value))

    facts = [f for f in data.get("facts", []) if f.get("category") and f.get("fact")]
    if facts:
        add_facts(facts)

    return len(facts)

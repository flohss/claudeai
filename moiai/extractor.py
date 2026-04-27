"""
Profile extraction engine — after each exchange, ask Claude to pull personal facts
from the conversation and merge them into persistent memory.
"""

import json
import math
from typing import Callable

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


# ── Batch extraction for imported files ───────────────────────────────────────

_BATCH_PROMPT = """\
Tu es un moteur d'extraction silencieux. Analyse les messages ci-dessous \
(écrits par une personne ou attribués à des personnes) et extrais toutes \
les informations personnelles sur la personne principale (l'utilisateur).

Retourne UNIQUEMENT un objet JSON valide :
{
  "profile_updates": {"clé": "valeur"},
  "facts": [{"category": "catégorie", "fact": "fait en une phrase"}]
}

Catégories : identité, famille, travail, santé, loisirs, valeurs, habitudes, \
projets, finances, localisation, relations, éducation, croyances, humeur, alimentation.

Règles :
- N'invente rien.
- profile_updates = faits stables (nom, âge, ville, métier…).
- Si rien à extraire : {"profile_updates": {}, "facts": []}.
- Aucun texte hors du JSON.

Messages :
"""

_CHUNK_WORDS = 1500


def _chunk_messages(messages: list[str], words_per_chunk: int = _CHUNK_WORDS) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    count = 0
    for msg in messages:
        w = len(msg.split())
        if count + w > words_per_chunk and current:
            chunks.append("\n".join(current))
            current = []
            count = 0
        current.append(msg)
        count += w
    if current:
        chunks.append("\n".join(current))
    return chunks


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def extract_from_messages(
    messages: list[str],
    progress_callback: Callable[[int, int], None] | None = None,
) -> int:
    """
    Extract personal facts from a list of messages (imported file).
    Splits into chunks and calls Claude on each. Returns total fact count.
    progress_callback(current_chunk, total_chunks) is called after each chunk.
    """
    if not messages:
        return 0

    chunks = _chunk_messages(messages)
    total = len(chunks)
    total_facts = 0

    client = _get_client()

    for i, chunk in enumerate(chunks, 1):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system="Tu es un extracteur JSON silencieux. Réponds uniquement en JSON valide.",
            messages=[{"role": "user", "content": _BATCH_PROMPT + chunk}],
        )
        data = _parse_json(response.content[0].text)

        for key, value in data.get("profile_updates", {}).items():
            if key and value:
                update_profile(str(key), str(value))

        facts = [f for f in data.get("facts", []) if f.get("category") and f.get("fact")]
        if facts:
            add_facts(facts)
        total_facts += len(facts)

        if progress_callback:
            progress_callback(i, total)

    return total_facts

"""
Profile extraction engine — after each exchange, ask Claude to pull personal facts
from the conversation and merge them into persistent memory.

Each fact carries a certainty level:
  certain   — stated as established fact ("je suis ingénieur")
  probable  — likely but not fully confirmed ("j'ai tendance à procrastiner")
  hypothèse — self-hypothesis, suspicion, possible diagnosis ("je pense être TDAH")
  réfuté    — explicitly retracted or contradicted
"""

import json
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
toutes les informations personnelles sur l'utilisateur.

Retourne UNIQUEMENT un objet JSON valide :
{
  "profile_updates": {
    "clé": "valeur"
  },
  "facts": [
    {
      "category": "catégorie",
      "fact": "fait précis rédigé avec le bon degré de certitude",
      "certainty": "certain|probable|hypothèse|réfuté"
    }
  ]
}

Catégories possibles : identité, famille, travail, santé, loisirs, valeurs, \
habitudes, projets, finances, localisation, relations, éducation, croyances, \
psychologie, alimentation, humeur.

Règle critique sur la certitude — tu DOIS distinguer :
- "certain"   : affirmé clairement sans nuance ("je suis développeur", "j'ai 32 ans")
- "probable"  : exprimé comme tendance ou quasi-certitude ("j'ai souvent du mal à dormir")
- "hypothèse" : auto-hypothèse, suspicion, diagnostic non confirmé, doute sur soi
                ("je pense être TDAH", "j'ai peut-être de l'anxiété", "je crois que je suis introverti")
- "réfuté"    : information explicitement annulée, corrigée ou contredite

Règles supplémentaires :
- Le texte du fait DOIT refléter la certitude : ne jamais écrire "a le TDAH" si l'utilisateur
  dit "je pense être TDAH" → écrire "pense peut-être avoir le TDAH (non diagnostiqué)"
- profile_updates = uniquement les faits "certain" et stables (nom, âge, ville, profession…)
- N'invente rien, n'infère pas au-delà de ce qui est dit.
- Si rien à extraire : {"profile_updates": {}, "facts": []}.
- Aucun texte hors du JSON.

Échange à analyser :
"""


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


def extract_and_store(user_msg: str, assistant_msg: str) -> int:
    """Extract personal info from one exchange and persist it. Returns fact count."""
    exchange = f"Utilisateur : {user_msg}\nAssistant : {assistant_msg}"

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="Tu es un extracteur JSON silencieux. Réponds uniquement en JSON valide.",
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT + exchange}],
    )

    data = _parse_json(response.content[0].text)

    # Only push certain facts to profile
    for key, value in data.get("profile_updates", {}).items():
        if key and value:
            update_profile(str(key), str(value))

    facts = [f for f in data.get("facts", []) if f.get("category") and f.get("fact")]
    if facts:
        return add_facts(facts)

    return 0


# ── Batch extraction for imported files ───────────────────────────────────────

_BATCH_PROMPT = """\
Tu es un moteur d'extraction silencieux. Analyse les messages ci-dessous \
et extrais toutes les informations personnelles sur la personne principale.

Retourne UNIQUEMENT un objet JSON valide :
{
  "profile_updates": {"clé": "valeur"},
  "facts": [
    {
      "category": "catégorie",
      "fact": "fait rédigé avec le bon degré de certitude",
      "certainty": "certain|probable|hypothèse|réfuté"
    }
  ]
}

Catégories : identité, famille, travail, santé, loisirs, valeurs, habitudes, \
projets, finances, localisation, relations, éducation, croyances, psychologie, \
alimentation, humeur.

Règle critique sur la certitude :
- "certain"   : affirmé sans ambiguïté
- "probable"  : quasi-certain, tendance claire
- "hypothèse" : supposition, doute, auto-diagnostic non confirmé
- "réfuté"    : annulé ou contredit

Le texte du fait DOIT refléter la certitude (jamais "a le TDAH" si c'est une hypothèse).
profile_updates = uniquement faits certains et stables.
Si rien : {"profile_updates": {}, "facts": []}.
Aucun texte hors du JSON.

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


def extract_from_messages(
    messages: list[str],
    progress_callback: Callable[[int, int], None] | None = None,
) -> int:
    """
    Extract personal facts from a list of messages (imported file).
    Splits into chunks and calls Claude on each. Returns total fact count.
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
            total_facts += add_facts(facts)

        if progress_callback:
            progress_callback(i, total)

    return total_facts

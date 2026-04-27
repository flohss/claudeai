"""
Profile extraction engine — uses Haiku (fast/cheap) to pull personal facts,
certainty levels, and current mood from each exchange.
"""

import json
from typing import Callable

from .api import MODEL_FAST, complete
from .memory import CERTAINTY_LEVELS, VALID_CATEGORIES, add_facts, log_mood, update_profile

# ── Prompts ────────────────────────────────────────────────────────────────────

_SYSTEM = "Tu es un extracteur JSON silencieux. Réponds uniquement en JSON valide."

_EXTRACTION_PROMPT = """\
Analyse l'échange et extrais toutes les informations personnelles sur l'utilisateur.

Retourne UNIQUEMENT ce JSON :
{
  "profile_updates": {"clé": "valeur"},
  "facts": [
    {
      "category": "catégorie",
      "fact": "fait rédigé avec le bon degré de certitude",
      "certainty": "certain|probable|hypothèse|réfuté"
    }
  ],
  "mood": {
    "valence": "positive|neutral|negative|mixed",
    "state": "description courte de l'état émotionnel en 5 mots max",
    "intensity": 3
  }
}

Catégories valides : identité, famille, relations, travail, éducation, localisation,
santé, psychologie, valeurs, croyances, loisirs, habitudes, projets, finances,
alimentation, humeur, autre.

Règles sur la certitude :
- "certain"   : affirmé clairement ("je suis développeur", "j'ai 32 ans")
- "probable"  : tendance quasi-certaine ("j'ai souvent du mal à dormir")
- "hypothèse" : auto-hypothèse, suspicion, diagnostic possible ("je pense être TDAH")
- "réfuté"    : explicitement annulé ou contredit

CRITIQUE : le texte du fait DOIT refléter la certitude.
Ne jamais écrire "a le TDAH" si l'utilisateur dit "je pense être TDAH".
Écrire à la place : "pense peut-être avoir le TDAH (non diagnostiqué)".

profile_updates = uniquement faits certains et stables (nom, âge, ville, métier).
mood.intensity : 1 (très faible) à 5 (très intense). 3 si neutre ou incertain.
Si rien à extraire : {"profile_updates": {}, "facts": [], "mood": {"valence": "neutral", "state": "", "intensity": 3}}.
Aucun texte hors du JSON.

Échange :
"""

_BATCH_PROMPT = """\
Analyse les messages et extrais toutes les informations personnelles.

Retourne UNIQUEMENT ce JSON :
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

Catégories valides : identité, famille, relations, travail, éducation, localisation,
santé, psychologie, valeurs, croyances, loisirs, habitudes, projets, finances,
alimentation, humeur, autre.

Règles certitude : certain=affirmé, probable=tendance, hypothèse=supposition, réfuté=annulé.
Texte du fait DOIT refléter la certitude (jamais "a le TDAH" si c'est une hypothèse).
profile_updates = uniquement faits certains et stables.
Si rien : {"profile_updates": {}, "facts": []}.
Aucun texte hors du JSON.

Messages :
"""

_CHUNK_WORDS = 1500


# ── JSON helpers ───────────────────────────────────────────────────────────────

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


def _apply_extraction(data: dict, store_mood: bool = False) -> int:
    """Persist profile_updates, facts, and optionally mood. Returns fact count."""
    for key, value in data.get("profile_updates", {}).items():
        if key and value:
            update_profile(str(key), str(value))

    raw_facts = data.get("facts", [])
    valid_facts = [
        f for f in raw_facts
        if f.get("category") and f.get("fact")
    ]
    inserted = add_facts(valid_facts) if valid_facts else 0

    if store_mood:
        mood = data.get("mood", {})
        valence = mood.get("valence", "")
        state = mood.get("state", "")
        intensity = mood.get("intensity", 3)
        if valence and state:
            log_mood(valence, state, intensity)

    return inserted


# ── Single-exchange extraction ─────────────────────────────────────────────────

def extract_and_store(user_msg: str, assistant_msg: str) -> int:
    """Extract facts + mood from one conversation exchange. Returns inserted fact count."""
    exchange = f"Utilisateur : {user_msg}\nAssistant : {assistant_msg}"
    raw = complete(_EXTRACTION_PROMPT + exchange, system=_SYSTEM, model=MODEL_FAST)
    data = _parse_json(raw)
    return _apply_extraction(data, store_mood=True)


# ── Batch extraction (imported files) ─────────────────────────────────────────

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
    Extract facts from a list of messages (imported file).
    Chunks by word count and calls Claude Haiku on each. Returns total inserted.
    """
    if not messages:
        return 0

    chunks = _chunk_messages(messages)
    total = len(chunks)
    total_inserted = 0

    for i, chunk in enumerate(chunks, 1):
        raw = complete(_BATCH_PROMPT + chunk, system=_SYSTEM, model=MODEL_FAST, max_tokens=1024)
        data = _parse_json(raw)
        total_inserted += _apply_extraction(data, store_mood=False)
        if progress_callback:
            progress_callback(i, total)

    return total_inserted

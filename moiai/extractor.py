"""
Profile extraction engine — uses Haiku (fast/cheap) to pull personal facts,
certainty levels, mood, named people, and goals from each exchange.
"""

import json
from typing import Callable

from .api import MODEL_FAST, complete
from .goals import add_extracted_goals
from .memory import CERTAINTY_LEVELS, VALID_CATEGORIES, add_facts, log_mood, update_profile
from .people import upsert_person

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
    "state": "description courte en 5 mots max",
    "intensity": 3
  },
  "people": [
    {"name": "Prénom", "relation": "frère|ami|collègue|…", "note": "info utile"}
  ],
  "goals": ["objectif formulé clairement"],
  "capsules": [
    {"content": "résumé de l'événement futur", "days": 7, "note": "question de suivi"}
  ]
}

Catégories valides pour facts : identité, famille, relations, travail, éducation,
localisation, santé, psychologie, valeurs, croyances, loisirs, habitudes, projets,
finances, alimentation, humeur, autre.

Règles sur la certitude :
- "certain"   : affirmé clairement ("je suis développeur", "j'ai 32 ans")
- "probable"  : tendance quasi-certaine ("j'ai souvent du mal à dormir")
- "hypothèse" : auto-hypothèse, suspicion, diagnostic possible ("je pense être TDAH")
- "réfuté"    : explicitement annulé ou contredit

CRITIQUE : le texte du fait DOIT refléter la certitude.
Ne jamais écrire "a le TDAH" si l'utilisateur dit "je pense être TDAH".
Écrire : "pense peut-être avoir le TDAH (non diagnostiqué)".

RÈGLE ABSOLUE : Extrais UNIQUEMENT les informations que l'Utilisateur affirme
sur lui-même. Ignore tout ce que dit l'Assistant — même s'il reformule, résume
ou déduit quelque chose sur l'utilisateur. Seules les déclarations directes de
l'Utilisateur comptent comme source de faits.

profile_updates = uniquement faits certains et stables (nom, âge, ville, métier).
people = uniquement les personnes AUTRES que l'utilisateur mentionnées par leur prénom/nom.
goals = intentions ou objectifs déclarés ("veux apprendre le piano", "objectif : perdre 5kg").
mood.intensity : 1 (très faible) à 5 (très intense). 3 si neutre.
capsules = événements futurs concrets mentionnés (entretien, voyage, rendez-vous, deadline,
  décision à prendre). days = délai estimé en jours avant l'événement.
  note = la question naturelle à poser à ce moment-là.
  Ne créer une capsule QUE si l'événement est précis et daté/délai estimable.
Si rien à extraire dans un champ, retourner liste/objet vide.
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
  ],
  "people": [
    {"name": "Prénom", "relation": "relation", "note": "info utile"}
  ],
  "goals": ["objectif clairement formulé"]
}

Catégories valides : identité, famille, relations, travail, éducation, localisation,
santé, psychologie, valeurs, croyances, loisirs, habitudes, projets, finances,
alimentation, humeur, autre.

Règles certitude : certain=affirmé, probable=tendance, hypothèse=supposition, réfuté=annulé.
Texte du fait DOIT refléter la certitude.
profile_updates = uniquement faits certains et stables.
Si rien dans un champ : liste/objet vide. Aucun texte hors du JSON.

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
    """Persist all extracted fields. Returns inserted fact count."""
    # Profile (only certain, stable facts)
    for key, value in data.get("profile_updates", {}).items():
        if key and value:
            update_profile(str(key), str(value))

    # Facts
    raw_facts = [f for f in data.get("facts", []) if f.get("category") and f.get("fact")]
    inserted = add_facts(raw_facts) if raw_facts else 0

    # Mood
    if store_mood:
        mood = data.get("mood", {})
        valence = mood.get("valence", "")
        state = mood.get("state", "")
        intensity = mood.get("intensity", 3)
        if valence and state:
            log_mood(valence, state, intensity)

    # People
    for p in data.get("people", []):
        name = p.get("name", "").strip()
        if name and len(name) >= 2:
            upsert_person(
                name=name,
                relation=p.get("relation"),
                note=p.get("note"),
            )

    # Goals
    goal_texts = [g.strip() for g in data.get("goals", []) if isinstance(g, str) and g.strip()]
    if goal_texts:
        add_extracted_goals(goal_texts)

    # Auto-capsules from future events
    for c in data.get("capsules", []):
        content = c.get("content", "").strip()
        days = c.get("days")
        note = c.get("note", "").strip() or None
        if content and isinstance(days, (int, float)) and 1 <= int(days) <= 730:
            try:
                from .capsule import add_auto_capsule
                add_auto_capsule(content, int(days), ai_note=note)
            except Exception:
                pass

    return inserted


# ── Single-exchange extraction ─────────────────────────────────────────────────

def extract_and_store(user_msg: str, assistant_msg: str) -> int:
    """Extract facts, mood, people, goals from one exchange. Returns inserted fact count."""
    exchange = (
        f"[UTILISATEUR — extraire d'ici]\n{user_msg}\n\n"
        f"[ASSISTANT — ignorer pour l'extraction]\n{assistant_msg}"
    )
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
    Extract from a list of messages (imported file).
    Chunks by word count, calls Haiku on each. Returns total inserted facts.
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

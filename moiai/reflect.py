"""
Reflection engine — pattern analysis, contradiction detection, weekly summary,
and life domain self-assessment.
"""

import json
import sqlite3
from datetime import datetime, timedelta

from .api import MODEL_FAST, MODEL_SMART, complete
from .memory import (
    _connect,
    get_all_facts,
    get_conversation_summaries,
    get_latest_narrative,
    get_profile,
    get_recent_mood,
)

# ── Life domains ───────────────────────────────────────────────────────────────

LIFE_DOMAINS = [
    "travail / carrière",
    "relations / famille",
    "santé / corps",
    "mental / émotions",
    "finances",
    "loisirs / créativité",
    "croissance personnelle",
    "sens / valeurs",
]


def _ensure_bilan_table() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS life_domain_scores (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                domain    TEXT    NOT NULL,
                score     INTEGER NOT NULL,
                timestamp TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bilan_ts ON life_domain_scores(timestamp DESC);
        """)


def save_domain_scores(scores: dict[str, int]) -> None:
    _ensure_bilan_table()
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO life_domain_scores (domain, score, timestamp) VALUES (?, ?, ?)",
            [(domain, score, now) for domain, score in scores.items()],
        )


def get_latest_domain_scores() -> dict[str, int]:
    _ensure_bilan_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT domain, score FROM life_domain_scores "
            "WHERE timestamp = (SELECT MAX(timestamp) FROM life_domain_scores)"
        ).fetchall()
    return {r["domain"]: r["score"] for r in rows}


def get_domain_history(domain: str, limit: int = 10) -> list[dict]:
    _ensure_bilan_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT score, timestamp FROM life_domain_scores "
            "WHERE domain = ? ORDER BY timestamp DESC LIMIT ?",
            (domain, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_bilan_context() -> str:
    scores = get_latest_domain_scores()
    if not scores:
        return ""
    lines = ["## Bilan de vie (auto-évaluation récente)"]
    for domain, score in scores.items():
        bar = "█" * score + "░" * (5 - score)
        lines.append(f"- {domain:<28} {bar} {score}/5")
    return "\n".join(lines)


# ── Contradiction detection ────────────────────────────────────────────────────

def _ensure_contradiction_table() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS contradictions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                fact1_id   INTEGER,
                fact2_id   INTEGER,
                explanation TEXT NOT NULL,
                resolved   INTEGER DEFAULT 0,
                timestamp  TEXT    NOT NULL
            );
        """)


def store_contradiction(fact1_id: int | None, fact2_id: int | None, explanation: str) -> None:
    _ensure_contradiction_table()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO contradictions (fact1_id, fact2_id, explanation, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (fact1_id, fact2_id, explanation, datetime.now().isoformat()),
        )


def get_unresolved_contradictions() -> list[dict]:
    _ensure_contradiction_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, fact1_id, fact2_id, explanation, timestamp "
            "FROM contradictions WHERE resolved = 0 ORDER BY timestamp DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def resolve_contradiction(cid: int) -> None:
    _ensure_contradiction_table()
    with _connect() as conn:
        conn.execute("UPDATE contradictions SET resolved = 1 WHERE id = ?", (cid,))


_CONTRADICTION_SYSTEM = "Tu es un détecteur de contradictions. Réponds uniquement en JSON valide."

_CONTRADICTION_PROMPT = """\
Examine ces faits sur une même personne et détecte les contradictions ou tensions claires.
Une contradiction = deux faits qui ne peuvent pas être vrais simultanément.
Une tension = deux faits qui révèlent une incohérence notable (valeur déclarée vs comportement).

Retourne UNIQUEMENT un tableau JSON (vide si aucune contradiction) :
[
  {
    "fact1": "texte du premier fait",
    "fact2": "texte du second fait",
    "explanation": "explication courte de la contradiction en français"
  }
]

Faits à analyser :
"""


def find_contradictions(max_per_category: int = 30) -> list[dict]:
    """
    Scan facts for contradictions using Claude Haiku.
    Returns list of {fact1, fact2, explanation}.
    """
    facts = get_all_facts()
    if len(facts) < 4:
        return []

    # Group by category and check categories with enough facts
    by_cat: dict[str, list[dict]] = {}
    for f in facts:
        by_cat.setdefault(f["category"], []).append(f)

    contradictions: list[dict] = []

    for cat, items in by_cat.items():
        if len(items) < 2:
            continue
        fact_lines = "\n".join(
            f"- [{f['certainty']}] {f['fact']}" for f in items[:max_per_category]
        )
        prompt = _CONTRADICTION_PROMPT + f"Catégorie: {cat}\n" + fact_lines
        try:
            raw = complete(prompt, system=_CONTRADICTION_SYSTEM, model=MODEL_FAST, max_tokens=512)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            results = json.loads(raw)
            contradictions.extend(results)
        except Exception:
            continue

    return contradictions


# ── Reflection / insights ──────────────────────────────────────────────────────

_REFLECT_SYSTEM = "Tu es un psychologue bienveillant et observateur. Réponds en français."

_REFLECT_PROMPT = """\
Voici tout ce que je sais sur cette personne. Analyse-le en profondeur et partage
tes observations sincères : patterns comportementaux, contradictions, angles morts,
thèmes récurrents, forces non reconnues, points de vigilance.

Règles :
- Parle directement à la personne (tu/toi), pas d'elle
- 4 à 6 observations concrètes, pas de généralités
- Formule les hypothèses avec précaution ("il me semble que...", "j'observe souvent...")
- Ne complimente pas pour complimenter — sois honnête
- Ne pose pas de questions — c'est une observation, pas un dialogue
- Longueur : 300 à 500 mots, prose fluide

Profil :
{profile}

Faits :
{facts}

Narration existante :
{narrative}

Humeur récente :
{mood}
"""


def generate_reflection() -> str:
    """Generate a deep personal insight reflection. Returns markdown text."""
    profile = get_profile()
    facts = get_all_facts()
    narrative = get_latest_narrative()
    mood = get_recent_mood(limit=5)

    profile_text = "\n".join(f"- {k}: {v}" for k, v in profile.items()) if profile else "Non renseigné"

    by_cat: dict[str, list[str]] = {}
    for f in facts:
        badge = CERTAINTY_BADGE_MAP.get(f.get("certainty", "certain"), "●")
        by_cat.setdefault(f["category"], []).append(f"{badge} {f['fact']}")
    facts_text = ""
    for cat, items in by_cat.items():
        facts_text += f"\n**{cat}**\n" + "\n".join(f"  - {i}" for i in items)

    mood_text = ""
    if mood:
        mood_text = "\n".join(
            f"- {m['timestamp'][:10]}: {m['valence']} — {m['state']}" for m in mood
        )

    prompt = _REFLECT_PROMPT.format(
        profile=profile_text,
        facts=facts_text or "Aucun fait encore",
        narrative=narrative or "Pas encore de narration",
        mood=mood_text or "Non enregistrée",
    )

    return complete(prompt, system=_REFLECT_SYSTEM, model=MODEL_SMART, max_tokens=2048)


CERTAINTY_BADGE_MAP = {
    "certain": "●", "probable": "◐", "hypothèse": "○", "réfuté": "✕"
}


# ── Weekly summary ─────────────────────────────────────────────────────────────

_WEEKLY_SYSTEM = "Tu es un assistant de réflexion personnelle. Réponds en français."

_WEEKLY_PROMPT = """\
Voici les échanges des 7 derniers jours entre l'utilisateur et son IA personnelle.
Génère une réflexion hebdomadaire bienveillante et utile :

- Ce qui a été évoqué (sujets principaux)
- Ce qui a été appris ou résolu
- Les tensions ou difficultés qui ont émergé
- Un ou deux points à continuer d'explorer la semaine prochaine

Parle directement à la personne (tu/toi). Prose fluide, 200-300 mots.

Échanges :
{exchanges}
"""


def generate_weekly_summary() -> str:
    """Summarize the past 7 days of conversation."""
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content, timestamp FROM conversations "
            "WHERE timestamp > ? ORDER BY id",
            (cutoff,),
        ).fetchall()

    if len(rows) < 4:
        return "Pas assez d'échanges cette semaine pour générer un résumé."

    exchanges = "\n".join(
        f"{r['role'].capitalize()} ({r['timestamp'][:10]}) : {r['content'][:300]}"
        for r in rows
    )
    prompt = _WEEKLY_PROMPT.format(exchanges=exchanges[:8000])
    return complete(prompt, system=_WEEKLY_SYSTEM, model=MODEL_FAST, max_tokens=1024)


# ── Startup briefing ───────────────────────────────────────────────────────────

_BRIEFING_SYSTEM = "Tu es un double personnel attentionné. Réponds en français, sois bref et naturel."

_BRIEFING_PROMPT = """\
L'utilisateur revient après une absence de {gap}. Date et heure actuelles : {now}.
Génère un message d'accueil court (2-3 phrases max).

Objectif : montrer que tu te souviens, sans faire un rapport. Une phrase de reconnexion
+ une question sur le fil le plus important laissé ouvert.

RÈGLE CRITIQUE : Si un fil ouvert mentionne un événement futur (pas encore passé par
rapport à la date actuelle), ne demande pas "comment ça s'est passé" — mentionne-le
avec anticipation ("tu as X bientôt, comment tu te sens ?").
Ne demande "comment ça s'est passé" que pour des événements clairement passés.

Informations disponibles :
Fils ouverts : {threads}
Objectifs actifs : {goals}
Humeur lors de la dernière session : {last_mood}
Faits récents intéressants : {recent_facts}

Ton message doit sembler naturel, pas robotique.
"""


def generate_startup_briefing(
    gap_hours: float,
    open_threads: list[str],
    active_goals: list[str],
    last_mood: str,
    recent_facts: list[str],
) -> str:
    """Generate a warm session-opening message referencing open threads."""
    if gap_hours < 2:
        return ""

    if gap_hours < 24:
        gap = f"{int(gap_hours)} heures"
    elif gap_hours < 48:
        gap = "hier"
    elif gap_hours < 168:
        gap = f"{int(gap_hours / 24)} jours"
    else:
        gap = f"{int(gap_hours / 168)} semaine(s)"

    from datetime import datetime as _dt
    now_str = _dt.now().strftime("%A %d/%m/%Y %Hh")

    threads_str = " | ".join(open_threads[:3]) if open_threads else "aucun"
    goals_str = " | ".join(active_goals[:3]) if active_goals else "aucun"
    recent_str = " | ".join(recent_facts[:3]) if recent_facts else "aucun"

    prompt = _BRIEFING_PROMPT.format(
        gap=gap,
        now=now_str,
        threads=threads_str,
        goals=goals_str,
        last_mood=last_mood or "non enregistrée",
        recent_facts=recent_str,
    )

    try:
        return complete(prompt, system=_BRIEFING_SYSTEM, model=MODEL_FAST, max_tokens=200)
    except Exception:
        return ""

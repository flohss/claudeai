"""
Question engine — structured life interview to build the user's personal memory.
Detects coverage gaps across life domains and generates targeted, context-aware questions.
"""

from datetime import datetime, timezone
from typing import Iterator

from .api import MODEL_CHAT, MODEL_FAST, complete, plain_block, stream_chat
from .memory import _connect, get_all_facts, get_profile

# ── Life domains ───────────────────────────────────────────────────────────────

INTERVIEW_DOMAINS = [
    {
        "key": "origines",
        "label": "Origines & enfance",
        "description": "origines familiales, ville natale, parents, frères/sœurs, école primaire, premiers souvenirs",
        "categories": ["identité", "famille", "localisation"],
    },
    {
        "key": "adolescence",
        "label": "Adolescence & lycée",
        "description": "collège, lycée, amis d'enfance, premières amours, passions naissantes, identité qui se forme",
        "categories": ["éducation", "relations", "loisirs", "psychologie"],
    },
    {
        "key": "etudes",
        "label": "Études & formation",
        "description": "études supérieures, orientation, formation professionnelle, moments décisifs, expériences universitaires",
        "categories": ["éducation", "travail"],
    },
    {
        "key": "carriere",
        "label": "Vie professionnelle",
        "description": "premier job, évolution de carrière, tournants professionnels, collègues marquants, satisfaction au travail",
        "categories": ["travail", "finances"],
    },
    {
        "key": "amour",
        "label": "Relations amoureuses",
        "description": "premières amours, relations importantes, ruptures, ce que l'amour a appris sur soi",
        "categories": ["relations", "psychologie"],
    },
    {
        "key": "amitie",
        "label": "Amitiés & entourage",
        "description": "amis proches, personnes importantes dans la vie, liens forts, gens perdus de vue",
        "categories": ["relations", "famille"],
    },
    {
        "key": "sante",
        "label": "Santé & bien-être",
        "description": "santé physique et mentale, habitudes de vie, épreuves de santé, ce qui aide à aller bien",
        "categories": ["santé", "habitudes", "alimentation"],
    },
    {
        "key": "valeurs",
        "label": "Valeurs & croyances",
        "description": "ce qui compte vraiment dans la vie, convictions, croyances, ce qui a évolué avec le temps",
        "categories": ["valeurs", "croyances", "psychologie"],
    },
    {
        "key": "passions",
        "label": "Passions & loisirs",
        "description": "hobbies, passions, activités qui donnent de l'énergie, découvertes qui ont changé la vie",
        "categories": ["loisirs", "habitudes"],
    },
    {
        "key": "voyages",
        "label": "Voyages & aventures",
        "description": "voyages marquants, découvertes culturelles, lieux qui ont compté, expériences hors du commun",
        "categories": ["loisirs", "autre"],
    },
    {
        "key": "epreuves",
        "label": "Épreuves & résilience",
        "description": "moments difficiles, deuils, échecs, comment on en est sorti et ce que ça a appris sur soi",
        "categories": ["psychologie", "santé", "autre"],
    },
    {
        "key": "fierte",
        "label": "Fiertés & réussites",
        "description": "moments de fierté, accomplissements personnels ou professionnels, ce dont on est le plus fier",
        "categories": ["psychologie", "travail", "autre"],
    },
    {
        "key": "projets",
        "label": "Projets & rêves",
        "description": "aspirations, rêves de vie, projets futurs, ce qu'on aimerait accomplir ou vivre avant de mourir",
        "categories": ["projets"],
    },
]

_DOMAIN_BY_KEY = {d["key"]: d for d in INTERVIEW_DOMAINS}

# ── DB helpers ─────────────────────────────────────────────────────────────────

def _init_table() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                domain    TEXT NOT NULL,
                question  TEXT NOT NULL,
                asked_at  TEXT NOT NULL
            )
        """)
        conn.commit()


def log_question(domain_key: str, question: str) -> None:
    _init_table()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO questions_log (domain, question, asked_at) VALUES (?, ?, ?)",
            (domain_key, question, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def get_asked_questions(domain_key: str) -> list[str]:
    _init_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT question FROM questions_log WHERE domain = ? ORDER BY asked_at DESC LIMIT 20",
            (domain_key,),
        ).fetchall()
    return [r[0] for r in rows]


def get_all_question_counts() -> dict[str, int]:
    _init_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT domain, COUNT(*) FROM questions_log GROUP BY domain"
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def get_total_questions_asked() -> int:
    _init_table()
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM questions_log").fetchone()
    return row[0] if row else 0


# ── Coverage analysis ──────────────────────────────────────────────────────────

def get_coverage_report() -> list[dict]:
    """Return domains sorted by coverage score (least covered first)."""
    facts = get_all_facts()
    cat_counts: dict[str, int] = {}
    for f in facts:
        cat = f.get("category", "autre")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    q_counts = get_all_question_counts()

    report = []
    for d in INTERVIEW_DOMAINS:
        fact_score = sum(cat_counts.get(c, 0) for c in d["categories"])
        q_count = q_counts.get(d["key"], 0)
        # Weight: facts are stronger signal than questions asked
        coverage_score = fact_score * 2 + q_count * 3
        report.append({
            **d,
            "fact_count": fact_score,
            "questions_asked": q_count,
            "coverage_score": coverage_score,
        })

    report.sort(key=lambda x: x["coverage_score"])
    return report


# ── Question generation ────────────────────────────────────────────────────────

_Q_SYSTEM = "Tu es un intervieweur empathique. Réponds UNIQUEMENT avec la question, sans guillemets, sans introduction, sans numérotation."

_Q_PROMPT = """\
Tu mènes un entretien de vie pour aider quelqu'un à documenter son histoire personnelle et construire sa mémoire.
Pose UNE seule question ouverte sur le domaine suivant.

Domaine : {label}
Ce domaine couvre : {description}

Profil connu de la personne :
{profile}

Faits déjà connus sur ce domaine :
{known_facts}

Questions déjà posées dans ce domaine (NE PAS répéter ni paraphraser) :
{asked}

Règles absolues :
- UNE seule question, courte, naturelle, intime, personnelle
- Formes acceptées : "Tu as…", "C'était comment…", "Il y a…", "Qu'est-ce qui…", "Tu te souviens…", "Comment tu as…"
- Si des faits existent déjà sur ce domaine : creuse plus profond, ne recommence pas à zéro
- Si aucun fait : commence par une question d'ouverture large mais concrète
- Jamais de liste, jamais de double question, jamais de préambule, jamais d'explication
- Juste la question, directement
"""


def generate_question(domain: dict, profile: dict | None = None, facts: list[dict] | None = None) -> str:
    """Generate a targeted, context-aware question for the given domain."""
    if profile is None:
        profile = get_profile()
    if facts is None:
        facts = get_all_facts()

    domain_facts = [f["fact"] for f in facts if f.get("category") in domain["categories"]]
    asked = get_asked_questions(domain["key"])

    profile_lines = "\n".join(f"- {k} : {v}" for k, v in list(profile.items())[:8]) or "Aucun"
    known_lines = "\n".join(f"- {f}" for f in domain_facts[:12]) or "Aucun"
    asked_lines = "\n".join(f"- {q}" for q in asked[:15]) or "Aucune"

    prompt = _Q_PROMPT.format(
        label=domain["label"],
        description=domain["description"],
        profile=profile_lines,
        known_facts=known_lines,
        asked=asked_lines,
    )
    q = complete(prompt, system=_Q_SYSTEM, model=MODEL_FAST, max_tokens=150)
    return q.strip().strip('"').strip("'").strip()


# ── Conversational streaming response ──────────────────────────────────────────

_REACT_SYSTEM = """\
Tu mènes un entretien de vie. L'utilisateur vient de répondre à ta question.
Réagis en 1-2 phrases courtes, chaleureuses, sincères — comme un ami qui écoute vraiment.
Relève un détail concret de ce qu'il a dit : une ville, un prénom, une émotion, un fait précis.
Puis pose la question suivante de façon naturelle, comme si elle découlait de la conversation.
Évite absolument : "Super !", "C'est fascinant !", "Incroyable !", "Merci pour ce partage.", "Je comprends."
Parle directement, en français naturel et spontané. Pas de mise en scène.
"""


def stream_reaction_and_question(
    domain_label: str,
    prev_question: str,
    answer: str,
    next_question: str,
) -> Iterator[str]:
    """Stream a warm reaction to the user's answer, then naturally introduce the next question."""
    user_content = (
        f"[Domaine actuel : {domain_label}]\n"
        f"Ta question : « {prev_question} »\n"
        f"Ma réponse : {answer}\n\n"
        f"[Réagis brièvement à ma réponse, puis pose-moi cette question de façon naturelle :]\n"
        f"{next_question}"
    )
    messages = [{"role": "user", "content": user_content}]
    return stream_chat(messages, system_blocks=[plain_block(_REACT_SYSTEM)], model=MODEL_CHAT)

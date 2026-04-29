"""
Question engine — structured life interview to build the user's personal memory.
Detects coverage gaps, escalates question depth, tracks session context.
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
        "description": "aspirations, rêves de vie, projets futurs, ce qu'on aimerait accomplir ou vivre",
        "categories": ["projets"],
    },
]

_DOMAIN_BY_KEY = {d["key"]: d for d in INTERVIEW_DOMAINS}

# ── Depth levels ───────────────────────────────────────────────────────────────

DEPTH_LEVELS = [
    {
        "level": 0,
        "label": "surface",
        "display": "◦ surface",
        "instruction": (
            "Niveau FACTUEL : explore les faits concrets. "
            "Qu'est-ce qui s'est passé, qui était là, où, quand. Questions ouvertes et légères."
        ),
    },
    {
        "level": 1,
        "label": "émotionnel",
        "display": "◉ émotions",
        "instruction": (
            "Niveau ÉMOTIONNEL : explore le ressenti et le sens. "
            "Comment ça se vivait, ce que ça signifiait, ce qui était beau ou difficile à l'époque."
        ),
    },
    {
        "level": 2,
        "label": "identitaire",
        "display": "● identité",
        "instruction": (
            "Niveau IDENTITAIRE : explore l'impact durable. "
            "Comment ça a forgé qui il/elle est aujourd'hui, ce que ça a appris sur soi-même, "
            "ce que ça a changé dans sa façon de voir le monde."
        ),
    },
]

DEPTH_THRESHOLD = 2  # questions per depth level before escalating

# ── Sensitivity detection ──────────────────────────────────────────────────────

_DISTRESS_SIGNALS = {
    "difficile", "douloureux", "douloureuse", "je préfère pas", "j'aime pas en parler",
    "triste", "tristesse", "traumatisant", "traumatisante", "je veux pas", "c'est compliqué",
    "ça fait mal", "dur", "pénible", "je préfère ne pas", "on passe", "pas envie",
    "j'aimerais pas", "c'est douloureux", "ça m'a beaucoup affecté", "pas facile",
    "je souffre", "souffert", "deuil", "perdu", "perdre",
}


def is_sensitive_answer(answer: str) -> bool:
    lower = answer.lower()
    return any(signal in lower for signal in _DISTRESS_SIGNALS)


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _init_table() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                domain     TEXT NOT NULL,
                question   TEXT NOT NULL,
                session_id TEXT,
                depth      INTEGER DEFAULT 0,
                asked_at   TEXT NOT NULL
            )
        """)
        # Migrations for existing installs
        for col, definition in [("session_id", "TEXT"), ("depth", "INTEGER DEFAULT 0")]:
            try:
                conn.execute(f"ALTER TABLE questions_log ADD COLUMN {col} {definition}")
            except Exception:
                pass
        conn.commit()


def log_question(domain_key: str, question: str, session_id: str = "", depth: int = 0) -> None:
    _init_table()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO questions_log (domain, question, session_id, depth, asked_at) VALUES (?, ?, ?, ?, ?)",
            (domain_key, question, session_id, depth, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def get_asked_questions(domain_key: str) -> list[str]:
    _init_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT question FROM questions_log WHERE domain = ? ORDER BY asked_at DESC LIMIT 25",
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


def get_last_session_info() -> dict | None:
    """Return info about the most recent questions session."""
    _init_table()
    with _connect() as conn:
        row = conn.execute(
            "SELECT session_id, MIN(asked_at), COUNT(*) "
            "FROM questions_log WHERE session_id IS NOT NULL AND session_id != '' "
            "GROUP BY session_id ORDER BY MIN(asked_at) DESC LIMIT 1"
        ).fetchone()
        if not row or not row[0]:
            return None
        session_id, started, count = row

        domains = conn.execute(
            "SELECT DISTINCT domain FROM questions_log WHERE session_id = ?",
            (session_id,),
        ).fetchall()

    domain_labels = [
        _DOMAIN_BY_KEY.get(d[0], {}).get("label", d[0]) for d in domains
    ]
    return {
        "session_id": session_id,
        "started": started[:16].replace("T", " "),  # "2024-01-15 14:32"
        "count": count,
        "domains": domain_labels,
    }


def find_domain_by_arg(arg: str) -> dict | None:
    """Find a domain by key or partial label match."""
    arg = arg.lower().strip()
    if not arg:
        return None
    # Exact key match
    if arg in _DOMAIN_BY_KEY:
        return _DOMAIN_BY_KEY[arg]
    # Partial label match
    for d in INTERVIEW_DOMAINS:
        if arg in d["label"].lower() or arg in d["key"].lower():
            return d
    return None


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

_Q_SYSTEM = (
    "Tu es un intervieweur de vie empathique et curieux. "
    "Réponds UNIQUEMENT avec la question, sans guillemets, sans introduction, sans numérotation."
)

_Q_PROMPT = """\
Tu mènes un entretien de vie approfondi pour aider quelqu'un à documenter son histoire personnelle.
Pose UNE seule question sur le domaine suivant.

Domaine : {label}
Ce domaine couvre : {description}

Profil connu :
{profile}

Faits déjà connus sur ce domaine :
{known_facts}

Faits RÉFUTÉS / corrigés (NE JAMAIS mentionner ni utiliser ces informations) :
{refuted_facts}

Échanges récents de cette session (utilise-les pour créer une continuité naturelle) :
{session_context}

Questions déjà posées dans ce domaine toutes sessions confondues (NE PAS répéter ni paraphraser) :
{asked}

{depth_instruction}

Règles absolues :
- UNE seule question, courte, naturelle, intime
- Si des échanges récents existent : appuie-toi dessus pour creuser, crée un fil narratif
- Si des faits sont connus : creuse plus profond plutôt que de recommencer à zéro
- Si aucun fait ni échange : commence par une question d'ouverture large mais concrète
- Jamais de liste, jamais de double question, jamais de préambule
- Juste la question, directement
"""


def generate_question(
    domain: dict,
    profile: dict | None = None,
    facts: list[dict] | None = None,
    session_transcript: list[dict] | None = None,
    depth: int = 0,
) -> str:
    """Generate a targeted question for the given domain, depth, and session context."""
    if profile is None:
        profile = get_profile()
    if facts is None:
        facts = get_all_facts()

    domain_facts_valid = [
        f["fact"] for f in facts
        if f.get("category") in domain["categories"] and f.get("certainty") != "réfuté"
    ]
    domain_facts_refuted = [
        f["fact"] for f in facts
        if f.get("category") in domain["categories"] and f.get("certainty") == "réfuté"
    ]
    asked = get_asked_questions(domain["key"])

    profile_lines = "\n".join(f"- {k} : {v}" for k, v in list(profile.items())[:8]) or "Aucun"
    known_lines = "\n".join(f"- {f}" for f in domain_facts_valid[:12]) or "Aucun"
    refuted_lines = "\n".join(f"- {f}" for f in domain_facts_refuted[:8])
    asked_lines = "\n".join(f"- {q}" for q in asked[:20]) or "Aucune"

    # Build session context from recent transcript (last 5 exchanges)
    recent = (session_transcript or [])[-5:]
    if recent:
        session_lines = "\n".join(
            f"Q: {ex['q']}\nR: {ex['a']}" for ex in recent
        )
    else:
        session_lines = "Aucun échange encore dans cette session."

    depth_info = DEPTH_LEVELS[min(depth, 2)]
    depth_instruction = f"Niveau de profondeur actuel : {depth_info['label'].upper()}\n{depth_info['instruction']}"

    prompt = _Q_PROMPT.format(
        label=domain["label"],
        description=domain["description"],
        profile=profile_lines,
        known_facts=known_lines,
        refuted_facts=refuted_lines or "Aucun",
        session_context=session_lines,
        asked=asked_lines,
        depth_instruction=depth_instruction,
    )
    q = complete(prompt, system=_Q_SYSTEM, model=MODEL_FAST, max_tokens=150)
    return q.strip().strip('"').strip("'").strip()


# ── Conversational streaming response ──────────────────────────────────────────

_REACT_SYSTEM = """\
Tu mènes un entretien de vie approfondi. L'utilisateur vient de répondre à ta question.

Ton rôle :
1. Réagis en 1-2 phrases courtes, chaleureuses, authentiques — comme un ami qui écoute vraiment.
   Relève un détail CONCRET de ce qu'il a dit (un prénom, un lieu, une émotion, une date).
   Pas de formules creuses ("Super !", "C'est fascinant !", "Merci pour ce partage.").

2. Si la réponse ouvre une piste intéressante non explorée, suis-la naturellement AVANT de poser
   la question suggérée — une courte question de suivi, puis enchaîne sur la suivante.

3. Si la réponse semble toucher un sujet douloureux (le mot SENSIBLE apparaît dans le contexte),
   réagis avec douceur, ne pousse pas, et propose de continuer ou de passer à autre chose.

4. Pose la question suivante de façon naturelle, comme si elle découlait de la conversation.

Français direct, spontané, chaleureux. Jamais de mise en scène.
"""


def stream_reaction_and_question(
    domain_label: str,
    prev_question: str,
    answer: str,
    next_question: str,
    session_transcript: list[dict] | None = None,
    sensitive: bool = False,
) -> Iterator[str]:
    """Stream a warm, context-aware reaction then introduce the next question."""
    # Build recent session context
    recent = (session_transcript or [])[-4:]
    if recent:
        history_lines = "\n".join(f"Q: {ex['q']}\nR: {ex['a']}" for ex in recent)
        history_block = f"\nÉchanges précédents cette session :\n{history_lines}\n"
    else:
        history_block = ""

    sensitive_tag = "\n[SENSIBLE : la réponse semble toucher un sujet douloureux]\n" if sensitive else ""

    user_content = (
        f"[Domaine : {domain_label}]{sensitive_tag}{history_block}\n"
        f"Ta dernière question : « {prev_question} »\n"
        f"Réponse : {answer}\n\n"
        f"[Question suivante à poser de façon naturelle :]\n{next_question}"
    )
    messages = [{"role": "user", "content": user_content}]
    return stream_chat(messages, system_blocks=[plain_block(_REACT_SYSTEM)], model=MODEL_CHAT)


# ── End-of-session narrative ───────────────────────────────────────────────────

_NARRATIVE_SYSTEM = (
    "Tu es un biographe. Écris en français naturel, littéraire et chaleureux. "
    "Troisième personne uniquement."
)

_NARRATIVE_PROMPT = """\
Voici les échanges d'une session d'interview de vie :

{qa_text}

Écris UN paragraphe narratif (6-10 phrases) qui capture l'essentiel de ce qui a été partagé.
À la troisième personne : "Il/Elle a grandi...", "Cette période...", "Ce qui l'a marqué...".
Sois concret, précis, évocateur. Mentionne des détails spécifiques.
Pas de titre, pas de liste, pas de résumé bullet. Juste le paragraphe.
"""


def generate_session_narrative(session_transcript: list[dict]) -> str:
    """Generate a short biographical narrative from the session's Q&A exchanges."""
    if not session_transcript:
        return ""
    qa_text = "\n\n".join(
        f"[{ex.get('domain', '')}]\nQ : {ex['q']}\nR : {ex['a']}"
        for ex in session_transcript
    )
    prompt = _NARRATIVE_PROMPT.format(qa_text=qa_text)
    return complete(prompt, system=_NARRATIVE_SYSTEM, model=MODEL_CHAT, max_tokens=500)

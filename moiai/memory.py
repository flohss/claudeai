"""
Persistent memory layer — SQLite-backed storage for conversations, profile, facts,
conversation summaries, and the condensed personal narrative.
"""

import difflib
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "memory.db"

# How similar two fact strings must be (0-1) to be considered duplicates
_DEDUP_THRESHOLD = 0.82


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after initial schema without breaking existing DBs."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(facts)")}
    if "certainty" not in cols:
        conn.execute("ALTER TABLE facts ADD COLUMN certainty TEXT NOT NULL DEFAULT 'certain'")


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                role      TEXT    NOT NULL,
                content   TEXT    NOT NULL,
                timestamp TEXT    NOT NULL,
                summarized INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                summary   TEXT    NOT NULL,
                up_to_id  INTEGER NOT NULL,
                timestamp TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profile (
                key       TEXT PRIMARY KEY,
                value     TEXT NOT NULL,
                updated   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS facts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                category  TEXT NOT NULL,
                fact      TEXT NOT NULL,
                source    TEXT,
                certainty TEXT    NOT NULL DEFAULT 'certain',
                confirmed INTEGER DEFAULT 1,
                timestamp TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS narrative (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                content   TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
        """)
        _migrate(conn)


# ── Conversations ──────────────────────────────────────────────────────────────

def save_message(role: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
            (role, content, datetime.now().isoformat()),
        )


def load_recent_messages(limit: int = 30) -> list[dict]:
    """Return recent unsummarized messages, plus summaries for older context."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations "
            "WHERE summarized = 0 ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def load_messages_for_summary(after_id: int = 0, limit: int = 60) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, role, content FROM conversations "
            "WHERE id > ? AND summarized = 0 ORDER BY id LIMIT ?",
            (after_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_messages_summarized(up_to_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET summarized = 1 WHERE id <= ?",
            (up_to_id,),
        )


def save_conversation_summary(summary: str, up_to_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversation_summaries (summary, up_to_id, timestamp) VALUES (?, ?, ?)",
            (summary, up_to_id, datetime.now().isoformat()),
        )
    mark_messages_summarized(up_to_id)


def get_conversation_summaries(limit: int = 5) -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT summary FROM conversation_summaries ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [r["summary"] for r in reversed(rows)]


def count_unsummarized_messages() -> int:
    with _connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE summarized = 0"
        ).fetchone()[0]


def count_messages() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]


def get_last_message_id() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT MAX(id) FROM conversations").fetchone()
    return row[0] or 0


# ── Profile ────────────────────────────────────────────────────────────────────

def update_profile(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO profile (key, value, updated) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
            (key, value, datetime.now().isoformat()),
        )


def delete_profile_key(key: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM profile WHERE key = ?", (key,))
        return cur.rowcount > 0


def get_profile() -> dict[str, str]:
    with _connect() as conn:
        rows = conn.execute("SELECT key, value FROM profile").fetchall()
    return {r["key"]: r["value"] for r in rows}


# ── Facts ──────────────────────────────────────────────────────────────────────

def _fact_is_duplicate(fact_text: str, existing: list[str]) -> bool:
    """Return True if fact_text is too similar to any existing fact."""
    fact_lower = fact_text.lower()
    for ex in existing:
        ratio = difflib.SequenceMatcher(None, fact_lower, ex.lower()).ratio()
        if ratio >= _DEDUP_THRESHOLD:
            return True
    return False


# Ordered from most to least certain — used for display and context priority
CERTAINTY_LEVELS = ("certain", "probable", "hypothèse", "réfuté")

# Emoji badges shown in CLI for each certainty level
CERTAINTY_BADGE = {
    "certain":   "●",
    "probable":  "◐",
    "hypothèse": "○",
    "réfuté":    "✕",
}


def add_facts(facts: list[dict]) -> int:
    """
    Insert facts, skipping near-duplicates. Returns the number actually inserted.
    facts: list of {category, fact, certainty?, source?}
    certainty: 'certain' | 'probable' | 'hypothèse' | 'réfuté'
    """
    now = datetime.now().isoformat()
    with _connect() as conn:
        existing_rows = conn.execute("SELECT fact, certainty FROM facts").fetchall()
        existing_texts = [r["fact"] for r in existing_rows]

        inserted = 0
        for f in facts:
            text = f.get("fact", "").strip()
            if not text or not f.get("category"):
                continue
            certainty = f.get("certainty", "certain")
            if certainty not in CERTAINTY_LEVELS:
                certainty = "certain"

            if _fact_is_duplicate(text, existing_texts):
                # On a near-match: update certainty if new one is more certain, bump confirmed
                conn.execute(
                    "UPDATE facts SET confirmed = confirmed + 1, "
                    "certainty = CASE "
                    "  WHEN certainty = 'réfuté' THEN certainty "
                    "  WHEN ? = 'certain' THEN 'certain' "
                    "  WHEN ? = 'probable' AND certainty = 'hypothèse' THEN 'probable' "
                    "  ELSE certainty END "
                    "WHERE fact = ?",
                    (certainty, certainty, text),
                )
                continue

            conn.execute(
                "INSERT INTO facts (category, fact, certainty, source, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (f["category"], text, certainty, f.get("source", ""), now),
            )
            existing_texts.append(text)
            inserted += 1
    return inserted


def get_all_facts() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, category, fact, certainty, confirmed, timestamp FROM facts "
            "ORDER BY confirmed DESC, timestamp DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_fact(fact_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        return cur.rowcount > 0


def search_facts(query: str) -> list[dict]:
    """Keyword search across facts and profile."""
    q = f"%{query.lower()}%"
    with _connect() as conn:
        fact_rows = conn.execute(
            "SELECT id, category, fact, certainty, confirmed, timestamp FROM facts "
            "WHERE LOWER(fact) LIKE ? OR LOWER(category) LIKE ? "
            "ORDER BY confirmed DESC",
            (q, q),
        ).fetchall()
        profile_rows = conn.execute(
            "SELECT key, value FROM profile WHERE LOWER(key) LIKE ? OR LOWER(value) LIKE ?",
            (q, q),
        ).fetchall()
    return {
        "facts": [dict(r) for r in fact_rows],
        "profile": {r["key"]: r["value"] for r in profile_rows},
    }


# ── Narrative (condensed memory) ───────────────────────────────────────────────

def save_narrative(content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO narrative (content, timestamp) VALUES (?, ?)",
            (content, datetime.now().isoformat()),
        )


def get_latest_narrative() -> str | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT content FROM narrative ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return row["content"] if row else None


def get_narrative_count() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM narrative").fetchone()[0]


# ── Context building ───────────────────────────────────────────────────────────

def _score_relevance(text: str, keywords: set[str]) -> int:
    """Count how many keywords appear in text (case-insensitive)."""
    t = text.lower()
    return sum(1 for kw in keywords if kw in t)


def _extract_keywords(messages: list[dict], min_len: int = 4) -> set[str]:
    """Pull content words from recent messages for relevance scoring."""
    stopwords = {
        "que", "qui", "quoi", "dans", "avec", "pour", "sur", "par", "une", "des",
        "les", "est", "sont", "cette", "cela", "mais", "donc", "alors", "aussi",
        "très", "plus", "bien", "peut", "tout", "fait", "être", "avoir", "comme",
        "the", "and", "for", "that", "this", "with", "from", "have", "you", "your",
        "what", "when", "where", "which", "there", "their", "they", "about",
    }
    words: set[str] = set()
    for msg in messages[-6:]:
        for word in msg.get("content", "").lower().split():
            word = word.strip(".,!?;:\"'()")
            if len(word) >= min_len and word not in stopwords:
                words.add(word)
    return words


def build_smart_context(recent_messages: list[dict] | None = None) -> str:
    """
    Build the knowledge block to inject into prompts.
    If recent_messages provided, rank facts by relevance to conversation.
    Always includes: narrative, full profile, top-N facts.
    """
    lines: list[str] = []

    # 1. Condensed narrative (highest priority — rich personal summary)
    narrative = get_latest_narrative()
    if narrative:
        lines.append("## Narration personnelle condensée")
        lines.append(narrative)
        lines.append("")

    # 2. Conversation summaries (recent memory beyond context window)
    summaries = get_conversation_summaries(limit=3)
    if summaries:
        lines.append("## Résumés des conversations passées")
        for s in summaries:
            lines.append(f"- {s}")
        lines.append("")

    # 3. Profile (always full)
    profile = get_profile()
    if profile:
        lines.append("## Profil")
        for k, v in profile.items():
            lines.append(f"- **{k}** : {v}")
        lines.append("")

    # 4. Facts — ranked by relevance then by confirmed count
    all_facts = get_all_facts()
    if all_facts:
        keywords = _extract_keywords(recent_messages or [])
        if keywords:
            scored = sorted(
                all_facts,
                key=lambda f: (_score_relevance(f["fact"], keywords), f["confirmed"]),
                reverse=True,
            )
        else:
            scored = all_facts  # already sorted by confirmed DESC

        # Exclude réfuté facts from active context (keep them in DB only)
        scored = [f for f in scored if f.get("certainty") != "réfuté"]

        # Inject up to 60 facts; the most relevant/confirmed ones first
        top = scored[:60]
        by_cat: dict[str, list[tuple[str, str]]] = {}
        for f in top:
            certainty = f.get("certainty", "certain")
            by_cat.setdefault(f["category"], []).append((f["fact"], certainty))

        lines.append("## Faits mémorisés")
        lines.append("(● certain  ◐ probable  ○ hypothèse à explorer)")
        for cat, items in by_cat.items():
            lines.append(f"**{cat}**")
            for fact_text, certainty in items:
                badge = CERTAINTY_BADGE.get(certainty, "●")
                lines.append(f"  {badge} {fact_text}")
        lines.append("")

    if not lines:
        return ""

    return "# Ce que je sais de toi\n\n" + "\n".join(lines)

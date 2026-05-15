"""
Persistent memory layer — SQLite with FTS5, indices, soft-delete, staleness
detection, mood logging, and smart context building.
"""

import difflib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .settings import get as _cfg

DB_PATH = Path(__file__).parent / "data" / "memory.db"

_DEDUP_THRESHOLD = 0.75

CERTAINTY_LEVELS = ("certain", "probable", "hypothèse", "réfuté")
CERTAINTY_BADGE = {
    "certain":   "●",
    "probable":  "◐",
    "hypothèse": "○",
    "réfuté":    "✕",
}

VALID_CATEGORIES = {
    "identité", "famille", "relations", "travail", "éducation", "localisation",
    "santé", "psychologie", "valeurs", "croyances", "loisirs", "habitudes",
    "projets", "finances", "alimentation", "humeur", "autre",
}

# Staleness thresholds
_STALE_DAYS = 180
_VERY_STALE_DAYS = 365


# ── Connection ─────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # better concurrent write performance
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema & migrations ────────────────────────────────────────────────────────

def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotent migrations for columns added after initial schema."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(facts)")}
    if "certainty" not in cols:
        conn.execute("ALTER TABLE facts ADD COLUMN certainty TEXT NOT NULL DEFAULT 'certain'")
    if "deleted_at" not in cols:
        conn.execute("ALTER TABLE facts ADD COLUMN deleted_at TEXT DEFAULT NULL")
    if "last_confirmed" not in cols:
        conn.execute("ALTER TABLE facts ADD COLUMN last_confirmed TEXT DEFAULT NULL")

    conv_cols = {r[1] for r in conn.execute("PRAGMA table_info(conversations)")}
    if "summarized" not in conv_cols:
        conn.execute("ALTER TABLE conversations ADD COLUMN summarized INTEGER DEFAULT 0")


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                summarized  INTEGER DEFAULT 0
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
                updated   TEXT NOT NULL,
                created   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS facts (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                category       TEXT    NOT NULL,
                fact           TEXT    NOT NULL,
                certainty      TEXT    NOT NULL DEFAULT 'certain',
                source         TEXT,
                confirmed      INTEGER DEFAULT 1,
                last_confirmed TEXT    DEFAULT NULL,
                deleted_at     TEXT    DEFAULT NULL,
                timestamp      TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS narrative (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                content   TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mood_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                valence   TEXT NOT NULL,
                state     TEXT NOT NULL,
                intensity INTEGER DEFAULT 3,
                timestamp TEXT NOT NULL
            );

            -- Indices for performance
            CREATE INDEX IF NOT EXISTS idx_facts_category   ON facts(category)  WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_facts_certainty  ON facts(certainty) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_facts_confirmed  ON facts(confirmed DESC) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_conv_summarized  ON conversations(summarized, id);
            CREATE INDEX IF NOT EXISTS idx_mood_timestamp   ON mood_log(timestamp DESC);

            -- FTS5 for full-text search across facts
            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
                fact, category,
                content=facts,
                content_rowid=id
            );

            -- Triggers to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
                INSERT INTO facts_fts(rowid, fact, category) VALUES (new.id, new.fact, new.category);
            END;
            CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
                INSERT INTO facts_fts(facts_fts, rowid, fact, category)
                VALUES('delete', old.id, old.fact, old.category);
            END;
            CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
                INSERT INTO facts_fts(facts_fts, rowid, fact, category)
                VALUES('delete', old.id, old.fact, old.category);
                INSERT INTO facts_fts(rowid, fact, category) VALUES (new.id, new.fact, new.category);
            END;
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
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations "
            "WHERE summarized = 0 ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def load_conversation_history(limit: int = 20) -> list[dict]:
    """For /historique — includes role, content, timestamp."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


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
        conn.execute("UPDATE conversations SET summarized = 1 WHERE id <= ?", (up_to_id,))


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
            "SELECT summary FROM conversation_summaries ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [r["summary"] for r in reversed(rows)]


def get_all_conversation_summaries() -> list[dict]:
    """Return all summaries with id and timestamp, oldest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, summary, timestamp FROM conversation_summaries ORDER BY id ASC"
        ).fetchall()
    return [dict(r) for r in rows]


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
    now = datetime.now().isoformat()
    with _connect() as conn:
        existing = conn.execute("SELECT key FROM profile WHERE key = ?", (key,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE profile SET value = ?, updated = ? WHERE key = ?",
                (value, now, key),
            )
        else:
            conn.execute(
                "INSERT INTO profile (key, value, updated, created) VALUES (?, ?, ?, ?)",
                (key, value, now, now),
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

def _normalize_category(cat: str) -> str:
    c = cat.lower().strip()
    return c if c in VALID_CATEGORIES else "autre"


_REFUTE_THRESHOLD = 0.40  # lower threshold for finding facts to mark as réfuté


def _fact_is_duplicate(fact_text: str, existing: list[str]) -> bool:
    fact_lower = fact_text.lower()
    for ex in existing:
        if difflib.SequenceMatcher(None, fact_lower, ex.lower()).ratio() >= _DEDUP_THRESHOLD:
            return True
    return False


def _find_fact_to_refute(refuted_text: str, existing_rows: list) -> int | None:
    """Find an existing non-réfuté fact that the refuted_text is correcting.

    Uses word-overlap + fuzzy ratio so short correction fragments ("2011")
    can match longer existing facts ("a emménagé le 1er avril 2011...").
    Returns the fact ID or None.
    """
    text_lower = refuted_text.lower()
    # Meaningful words (len > 2, not common stop words)
    _STOP = {"les", "des", "une", "avec", "dans", "sur", "par", "que", "qui", "pas", "non"}
    words = [w for w in text_lower.split() if len(w) > 2 and w not in _STOP]

    best_id: int | None = None
    best_score: float = _REFUTE_THRESHOLD

    for row in existing_rows:
        if row["certainty"] == "réfuté":
            continue
        fact_lower = row["fact"].lower()

        fuzzy = difflib.SequenceMatcher(None, text_lower, fact_lower).ratio()
        word_hits = sum(1 for w in words if w in fact_lower)
        word_score = (word_hits / max(len(words), 1)) * 0.85

        score = max(fuzzy, word_score)
        if score > best_score:
            best_score = score
            best_id = row["id"]

    return best_id


def add_facts(facts: list[dict]) -> int:
    now = datetime.now().isoformat()
    with _connect() as conn:
        existing_rows = conn.execute(
            "SELECT id, fact, certainty FROM facts WHERE deleted_at IS NULL"
        ).fetchall()
        existing_texts = [r["fact"] for r in existing_rows]

        inserted = 0
        for f in facts:
            text = f.get("fact", "").strip()
            if not text or not f.get("category"):
                continue
            category = _normalize_category(f["category"])
            certainty = f.get("certainty", "certain")
            if certainty not in CERTAINTY_LEVELS:
                certainty = "certain"

            # ── Réfuté: find and update the wrong existing fact ────────────────
            if certainty == "réfuté":
                target_id = _find_fact_to_refute(text, existing_rows)
                if target_id:
                    conn.execute(
                        "UPDATE facts SET certainty = 'réfuté', last_confirmed = ? WHERE id = ?",
                        (now, target_id),
                    )
                else:
                    # No match found — insert as réfuté marker for future dedup
                    conn.execute(
                        "INSERT INTO facts (category, fact, certainty, source, last_confirmed, timestamp) "
                        "VALUES (?, ?, 'réfuté', ?, ?, ?)",
                        (category, text, f.get("source", ""), now, now),
                    )
                    existing_texts.append(text)
                continue

            # ── Normal dedup ───────────────────────────────────────────────────
            if _fact_is_duplicate(text, existing_texts):
                conn.execute(
                    "UPDATE facts SET confirmed = confirmed + 1, last_confirmed = ?, "
                    "certainty = CASE "
                    "  WHEN certainty = 'réfuté' THEN certainty "
                    "  WHEN ? = 'certain' THEN 'certain' "
                    "  WHEN ? = 'probable' AND certainty = 'hypothèse' THEN 'probable' "
                    "  ELSE certainty END "
                    "WHERE fact = ? AND deleted_at IS NULL",
                    (now, certainty, certainty, text),
                )
                continue

            conn.execute(
                "INSERT INTO facts (category, fact, certainty, source, last_confirmed, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (category, text, certainty, f.get("source", ""), now, now),
            )
            existing_texts.append(text)
            inserted += 1
    return inserted


def get_all_facts(include_deleted: bool = False) -> list[dict]:
    where = "" if include_deleted else "WHERE deleted_at IS NULL"
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT id, category, fact, certainty, confirmed, last_confirmed, timestamp "
            f"FROM facts {where} ORDER BY confirmed DESC, timestamp DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_fact_by_id(fact_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, category, fact, certainty, confirmed, timestamp "
            "FROM facts WHERE id = ?",
            (fact_id,),
        ).fetchone()
    return dict(row) if row else None


def update_fact(fact_id: int, new_text: str | None = None, new_certainty: str | None = None) -> bool:
    updates: list[str] = []
    params: list = []
    if new_text:
        updates.append("fact = ?")
        params.append(new_text.strip())
    if new_certainty and new_certainty in CERTAINTY_LEVELS:
        updates.append("certainty = ?")
        params.append(new_certainty)
    if not updates:
        return False
    updates.append("last_confirmed = ?")
    params.append(datetime.now().isoformat())
    params.append(fact_id)
    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE facts SET {', '.join(updates)} WHERE id = ? AND deleted_at IS NULL",
            params,
        )
    return cur.rowcount > 0


def soft_delete_fact(fact_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE facts SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (datetime.now().isoformat(), fact_id),
        )
    return cur.rowcount > 0


def delete_fact(fact_id: int) -> bool:
    """Soft delete — marks deleted_at, preserves row for audit."""
    return soft_delete_fact(fact_id)


def get_recent_facts(minutes: int = 30) -> list[dict]:
    """Return facts added in the last N minutes, ordered most recent first."""
    cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, category, fact, certainty, timestamp "
            "FROM facts WHERE deleted_at IS NULL AND timestamp >= ? "
            "ORDER BY timestamp DESC",
            (cutoff,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_stale_facts(days: int = _STALE_DAYS) -> list[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, category, fact, certainty, confirmed, timestamp "
            "FROM facts WHERE deleted_at IS NULL "
            "AND (last_confirmed < ? OR (last_confirmed IS NULL AND timestamp < ?))",
            (cutoff, cutoff),
        ).fetchall()
    return [dict(r) for r in rows]


def fact_age_badge(timestamp: str) -> str:
    """Return a staleness badge string for display, or '' if fresh."""
    try:
        dt = datetime.fromisoformat(timestamp)
    except ValueError:
        return ""
    age_days = (datetime.now() - dt).days
    if age_days >= _VERY_STALE_DAYS:
        return f" [dim]⌛ {age_days // 365}a[/dim]"
    if age_days >= _STALE_DAYS:
        return f" [dim]⏳ {age_days // 30}m[/dim]"
    return ""


def search_facts(query: str, limit: int = 30) -> dict:
    """Full-text search across facts (FTS5) and profile (LIKE fallback)."""
    with _connect() as conn:
        # FTS5 search on facts
        try:
            fts_rows = conn.execute(
                "SELECT f.id, f.category, f.fact, f.certainty, f.confirmed, f.timestamp "
                "FROM facts f JOIN facts_fts ON f.id = facts_fts.rowid "
                "WHERE facts_fts MATCH ? AND f.deleted_at IS NULL "
                "ORDER BY rank LIMIT ?",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS not available or query syntax error — fall back to LIKE
            q = f"%{query.lower()}%"
            fts_rows = conn.execute(
                "SELECT id, category, fact, certainty, confirmed, timestamp FROM facts "
                "WHERE (LOWER(fact) LIKE ? OR LOWER(category) LIKE ?) AND deleted_at IS NULL "
                "ORDER BY confirmed DESC LIMIT ?",
                (q, q, limit),
            ).fetchall()

        # Profile search (LIKE)
        q = f"%{query.lower()}%"
        profile_rows = conn.execute(
            "SELECT key, value FROM profile WHERE LOWER(key) LIKE ? OR LOWER(value) LIKE ?",
            (q, q),
        ).fetchall()

    return {
        "facts": [dict(r) for r in fts_rows],
        "profile": {r["key"]: r["value"] for r in profile_rows},
    }


def search_summaries(query: str, limit: int = 5) -> list[str]:
    """Search conversation summaries and narrative for a query string."""
    q = f"%{query.lower()}%"
    results: list[str] = []
    with _connect() as conn:
        try:
            rows = conn.execute(
                "SELECT summary FROM conversation_summaries "
                "WHERE LOWER(summary) LIKE ? ORDER BY id DESC LIMIT ?",
                (q, limit),
            ).fetchall()
            results.extend(r["summary"] for r in rows)
        except sqlite3.OperationalError:
            pass

        try:
            row = conn.execute(
                "SELECT content FROM narratives WHERE LOWER(content) LIKE ? ORDER BY id DESC LIMIT 1",
                (q,),
            ).fetchone()
            if row:
                results.append("[Narration] " + row["content"][:400])
        except sqlite3.OperationalError:
            pass
    return results


# ── Mood log ───────────────────────────────────────────────────────────────────

def log_mood(valence: str, state: str, intensity: int = 3) -> None:
    valid_valences = {"positive", "neutral", "negative", "mixed"}
    if valence not in valid_valences:
        valence = "neutral"
    intensity = max(1, min(5, intensity))
    with _connect() as conn:
        conn.execute(
            "INSERT INTO mood_log (valence, state, intensity, timestamp) VALUES (?, ?, ?, ?)",
            (valence, state, intensity, datetime.now().isoformat()),
        )


def get_recent_mood(limit: int = 5) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT valence, state, intensity, timestamp FROM mood_log "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_mood_summary() -> str:
    """One-line mood summary for context injection."""
    recent = get_recent_mood(limit=3)
    if not recent:
        return ""
    latest = recent[0]
    state_desc = f"{latest['valence']} — {latest['state']}"
    if len(recent) > 1:
        valences = [m["valence"] for m in recent]
        if valences.count("negative") >= 2:
            state_desc += " (tendance négative récente)"
        elif valences.count("positive") >= 2:
            state_desc += " (tendance positive récente)"
    return state_desc


def get_mood_by_day(days: int = 30) -> list[dict]:
    """Return the last mood entry per day for the past N days."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DATE(timestamp) as day, valence, state, intensity "
            "FROM mood_log WHERE timestamp > ? ORDER BY timestamp",
            (cutoff,),
        ).fetchall()

    by_day: dict[str, dict] = {}
    for r in rows:
        by_day[r["day"]] = dict(r)  # keep last entry of each day

    return [by_day[d] for d in sorted(by_day)]


# ── Narrative ──────────────────────────────────────────────────────────────────

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
    t = text.lower()
    return sum(1 for kw in keywords if kw in t)


def _extract_keywords(messages: list[dict], min_len: int = 4) -> set[str]:
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


def get_dynamic_facts(user_message: str, limit: int = 15) -> list[dict]:
    """Return facts most relevant to the current user message — for dynamic context injection."""
    import re as _re
    stopwords = {
        "que", "qui", "quoi", "dans", "avec", "pour", "sur", "par", "une", "des",
        "les", "est", "sont", "cette", "cela", "mais", "donc", "alors", "aussi",
        "très", "plus", "bien", "peut", "tout", "fait", "être", "avoir", "comme",
        "moi", "toi", "lui", "elle", "nous", "vous", "leur", "eux", "mon", "ton",
        "son", "notre", "votre", "mes", "tes", "ses", "nos", "vos", "ses",
    }
    words = {
        w.lower().strip(".,!?;:\"'()")
        for w in _re.split(r'\W+', user_message)
        if len(w) >= 3
    } - stopwords
    if not words:
        return []
    all_facts = get_all_facts()
    active = [f for f in all_facts if f.get("certainty") != "réfuté"]
    scored = [(f, _score_relevance(f["fact"], words)) for f in active]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [f for f, score in scored if score > 0][:limit]


def build_smart_context(recent_messages: list[dict] | None = None) -> str:
    lines: list[str] = []

    # 1. Narrative
    narrative = get_latest_narrative()
    if narrative:
        lines.append("## Narration personnelle condensée")
        lines.append(narrative)
        lines.append("")

    # 2. Conversation summaries
    summaries = get_conversation_summaries(limit=_cfg("résumés_contexte"))
    if summaries:
        lines.append("## Résumés des conversations passées")
        for s in summaries:
            lines.append(f"- {s}")
        lines.append("")

    # 4. Profile
    profile = get_profile()
    if profile:
        lines.append("## Profil")
        for k, v in profile.items():
            lines.append(f"- **{k}** : {v}")
        lines.append("")

    # 5. Facts — ranked by relevance + confirmed, capped at 60
    all_facts = get_all_facts()
    if all_facts:
        keywords = _extract_keywords(recent_messages or [])

        # Sort: réfuté excluded, hypothèse last, then by relevance + confirmed
        active = [f for f in all_facts if f.get("certainty") != "réfuté"]
        if keywords:
            active.sort(
                key=lambda f: (_score_relevance(f["fact"], keywords), f["confirmed"]),
                reverse=True,
            )

        top = active[:_cfg("faits_contexte")]
        by_cat: dict[str, list[tuple[str, str]]] = {}
        for f in top:
            by_cat.setdefault(f["category"], []).append((f["fact"], f.get("certainty", "certain")))

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

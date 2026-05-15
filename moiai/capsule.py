"""
Time capsule — messages from the user to their future self.
Auto-capsules can also be created by the AI when it detects future events.
"""

import re
from datetime import datetime, timedelta

from .memory import _connect


def _ensure_table() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS capsules (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                content    TEXT    NOT NULL,
                open_at    TEXT    NOT NULL,
                ai_note    TEXT    DEFAULT NULL,
                source     TEXT    NOT NULL DEFAULT 'user',
                created_at TEXT    NOT NULL,
                opened     INTEGER DEFAULT 0,
                opened_at  TEXT    DEFAULT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_capsules_open_at ON capsules(open_at);
        """)


def add_capsule(
    content: str,
    open_at: datetime,
    ai_note: str | None = None,
    source: str = "user",
) -> int:
    _ensure_table()
    now = datetime.now().isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO capsules (content, open_at, ai_note, source, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (content.strip(), open_at.isoformat(), ai_note, source, now),
        )
    return cur.lastrowid


def add_auto_capsule(content: str, days: int, ai_note: str | None = None) -> int:
    """AI-created capsule, opens in `days` days."""
    open_at = datetime.now() + timedelta(days=days)
    return add_capsule(content, open_at, ai_note=ai_note, source="auto")


def get_due_capsules() -> list[dict]:
    """Return capsules whose open_at <= now and not yet opened."""
    _ensure_table()
    now = datetime.now().isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, content, open_at, ai_note, source, created_at "
            "FROM capsules WHERE open_at <= ? AND opened = 0 ORDER BY open_at",
            (now,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_opened(capsule_id: int) -> None:
    _ensure_table()
    with _connect() as conn:
        conn.execute(
            "UPDATE capsules SET opened = 1, opened_at = ? WHERE id = ?",
            (datetime.now().isoformat(), capsule_id),
        )


def get_all_capsules() -> list[dict]:
    _ensure_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, content, open_at, ai_note, source, created_at, opened "
            "FROM capsules ORDER BY open_at",
        ).fetchall()
    return [dict(r) for r in rows]


def delete_capsule(capsule_id: int) -> bool:
    _ensure_table()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM capsules WHERE id = ?", (capsule_id,))
    return cur.rowcount > 0


def parse_delay(text: str) -> datetime | None:
    """
    Parse natural delay expressions into a datetime.
    Understands: 'dans 3 jours', 'dans 2 semaines', 'dans 1 mois',
    ISO date '2025-06-01', French date '15/06/2025'.
    """
    t = text.lower().strip()

    m = re.search(r"dans\s+(\d+)\s+(jour|jours|semaine|semaines|mois|an|ans)", t)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if "jour" in unit:
            return datetime.now() + timedelta(days=n)
        if "semaine" in unit:
            return datetime.now() + timedelta(weeks=n)
        if "mois" in unit:
            return datetime.now() + timedelta(days=n * 30)
        if "an" in unit:
            return datetime.now() + timedelta(days=n * 365)

    m = re.search(r"(\d{4}-\d{2}-\d{2})", t)
    if m:
        try:
            return datetime.fromisoformat(m.group(1))
        except ValueError:
            pass

    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    return None

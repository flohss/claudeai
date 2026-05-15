"""
Goal tracking — explicit user-declared goals plus auto-extracted ones.
Stored in SQLite, surfaced in /objectifs and injected into context.
"""

import sqlite3
from datetime import datetime

from .memory import _connect

GOAL_STATUSES = ("active", "achieved", "abandoned", "paused")


def _ensure_table() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                text       TEXT    NOT NULL,
                deadline   TEXT    DEFAULT NULL,
                status     TEXT    NOT NULL DEFAULT 'active',
                source     TEXT    NOT NULL DEFAULT 'user',
                created_at TEXT    NOT NULL,
                updated_at TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
        """)


def add_goal(text: str, deadline: str | None = None, source: str = "user") -> int:
    _ensure_table()
    now = datetime.now().isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO goals (text, deadline, status, source, created_at, updated_at) "
            "VALUES (?, ?, 'active', ?, ?, ?)",
            (text.strip(), deadline, source, now, now),
        )
    return cur.lastrowid


def get_active_goals() -> list[dict]:
    _ensure_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, text, deadline, status, source, created_at "
            "FROM goals WHERE status = 'active' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_goals() -> list[dict]:
    _ensure_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, text, deadline, status, source, created_at "
            "FROM goals ORDER BY status, created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_goal_status(goal_id: int, status: str) -> bool:
    if status not in GOAL_STATUSES:
        return False
    _ensure_table()
    now = datetime.now().isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE goals SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, goal_id),
        )
    return cur.rowcount > 0


def delete_goal(goal_id: int) -> bool:
    _ensure_table()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    return cur.rowcount > 0


def get_goal_by_id(goal_id: int) -> dict | None:
    _ensure_table()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, text, deadline, status, source, created_at FROM goals WHERE id = ?",
            (goal_id,),
        ).fetchone()
    return dict(row) if row else None


def add_extracted_goals(goal_texts: list[str]) -> int:
    """Add goals extracted from conversation (source='extracted'). Skip near-duplicates."""
    import difflib
    _ensure_table()
    existing = get_all_goals()
    existing_texts = [g["text"].lower() for g in existing]
    inserted = 0
    for text in goal_texts:
        text = text.strip()
        if not text:
            continue
        is_dup = any(
            difflib.SequenceMatcher(None, text.lower(), ex).ratio() > 0.8
            for ex in existing_texts
        )
        if not is_dup:
            add_goal(text, source="extracted")
            existing_texts.append(text.lower())
            inserted += 1
    return inserted


def get_goals_context() -> str:
    """One-block summary of active goals for context injection."""
    goals = get_active_goals()
    if not goals:
        return ""
    lines = ["## Objectifs actifs déclarés"]
    for g in goals[:10]:
        dl = f" (avant le {g['deadline'][:10]})" if g.get("deadline") else ""
        lines.append(f"- {g['text']}{dl}")
    return "\n".join(lines)

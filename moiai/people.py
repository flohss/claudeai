"""
Named-person relationship map — tracks people mentioned in conversation
with their relation type, mini-profile notes, and last mention date.
"""

import difflib
import sqlite3
from datetime import datetime

from .memory import _connect


def _ensure_table() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS people (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT    NOT NULL,
                relation       TEXT    DEFAULT NULL,
                notes          TEXT    DEFAULT NULL,
                last_mentioned TEXT    NOT NULL,
                created_at     TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);
            CREATE INDEX IF NOT EXISTS idx_people_last ON people(last_mentioned DESC);
        """)


def _find_by_name(conn: sqlite3.Connection, name: str) -> dict | None:
    rows = conn.execute(
        "SELECT id, name, relation, notes, last_mentioned FROM people "
        "WHERE LOWER(name) = LOWER(?)",
        (name,),
    ).fetchall()
    if rows:
        return dict(rows[0])
    # Fuzzy match
    all_rows = conn.execute("SELECT id, name, relation, notes, last_mentioned FROM people").fetchall()
    for r in all_rows:
        if difflib.SequenceMatcher(None, name.lower(), r["name"].lower()).ratio() > 0.85:
            return dict(r)
    return None


def upsert_person(name: str, relation: str | None = None, note: str | None = None) -> int:
    """Insert or update a person. Returns the person's ID."""
    _ensure_table()
    now = datetime.now().isoformat()
    with _connect() as conn:
        existing = _find_by_name(conn, name)
        if existing:
            pid = existing["id"]
            updates: list[str] = ["last_mentioned = ?"]
            params: list = [now]
            if relation and not existing.get("relation"):
                updates.append("relation = ?")
                params.append(relation)
            if note:
                old_notes = existing.get("notes") or ""
                new_notes = (old_notes + "\n" + note).strip() if old_notes else note
                updates.append("notes = ?")
                params.append(new_notes[:2000])
            params.append(pid)
            conn.execute(f"UPDATE people SET {', '.join(updates)} WHERE id = ?", params)
            return pid
        else:
            cur = conn.execute(
                "INSERT INTO people (name, relation, notes, last_mentioned, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, relation, note, now, now),
            )
            return cur.lastrowid


def get_all_people() -> list[dict]:
    _ensure_table()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, relation, notes, last_mentioned FROM people "
            "ORDER BY last_mentioned DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_person_by_id(pid: int) -> dict | None:
    _ensure_table()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, relation, notes, last_mentioned FROM people WHERE id = ?",
            (pid,),
        ).fetchone()
    return dict(row) if row else None


def delete_person(pid: int) -> bool:
    _ensure_table()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM people WHERE id = ?", (pid,))
    return cur.rowcount > 0


def get_people_context(limit: int = 8) -> str:
    """Compact people summary for context injection."""
    people = get_all_people()
    if not people:
        return ""
    lines = ["## Personnes dans ta vie"]
    for p in people[:limit]:
        rel = f" ({p['relation']})" if p.get("relation") else ""
        note = f" — {p['notes'][:80]}" if p.get("notes") else ""
        lines.append(f"- **{p['name']}**{rel}{note}")
    return "\n".join(lines)

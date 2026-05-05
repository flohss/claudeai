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


def _normalize_name(name: str) -> str:
    """First word title-cased, remaining words uppercased (last name convention)."""
    parts = name.strip().split()
    if len(parts) <= 1:
        return name.strip().title()
    return parts[0].title() + " " + " ".join(p.upper() for p in parts[1:])


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
    name = _normalize_name(name)
    now = datetime.now().isoformat()
    with _connect() as conn:
        existing = _find_by_name(conn, name)
        if existing:
            pid = existing["id"]
            updates: list[str] = ["last_mentioned = ?"]
            params: list = [now]
            if relation:
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


def merge_people(pid_keep: int, pid_delete: int) -> bool:
    """Merge pid_delete into pid_keep: combine notes, keep best relation, delete duplicate."""
    _ensure_table()
    with _connect() as conn:
        keep = conn.execute(
            "SELECT id, name, relation, notes FROM people WHERE id = ?", (pid_keep,)
        ).fetchone()
        drop = conn.execute(
            "SELECT id, name, relation, notes FROM people WHERE id = ?", (pid_delete,)
        ).fetchone()
        if not keep or not drop:
            return False

        relation = keep["relation"] or drop["relation"]
        notes_parts = [p for p in [keep["notes"], drop["notes"]] if p]
        notes = "\n".join(notes_parts)[:2000] if notes_parts else None

        conn.execute(
            "UPDATE people SET relation = ?, notes = ?, last_mentioned = ? WHERE id = ?",
            (relation, notes, datetime.now().isoformat(), pid_keep),
        )
        conn.execute("DELETE FROM people WHERE id = ?", (pid_delete,))
    return True


def update_person(pid: int, name: str | None = None, relation: str | None = None) -> bool:
    _ensure_table()
    updates: list[str] = []
    params: list = []
    if name:
        updates.append("name = ?")
        params.append(_normalize_name(name))
    if relation is not None:
        updates.append("relation = ?")
        params.append(relation)
    if not updates:
        return False
    params.append(pid)
    with _connect() as conn:
        cur = conn.execute(f"UPDATE people SET {', '.join(updates)} WHERE id = ?", params)
    return cur.rowcount > 0


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

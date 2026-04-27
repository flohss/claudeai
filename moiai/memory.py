"""
Persistent memory layer — SQLite-backed storage for conversations and personal profile.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "memory.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                role      TEXT    NOT NULL,
                content   TEXT    NOT NULL,
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
                timestamp TEXT NOT NULL
            );
        """)


# ── Conversations ──────────────────────────────────────────────────────────────

def save_message(role: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
            (role, content, datetime.now().isoformat()),
        )


def load_recent_messages(limit: int = 40) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def count_messages() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]


# ── Profile ────────────────────────────────────────────────────────────────────

def update_profile(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO profile (key, value, updated) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
            (key, value, datetime.now().isoformat()),
        )


def get_profile() -> dict[str, str]:
    with _connect() as conn:
        rows = conn.execute("SELECT key, value FROM profile").fetchall()
    return {r["key"]: r["value"] for r in rows}


# ── Facts ──────────────────────────────────────────────────────────────────────

def add_facts(facts: list[dict]) -> None:
    """facts: list of {category, fact, source}"""
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO facts (category, fact, source, timestamp) VALUES (?, ?, ?, ?)",
            [(f["category"], f["fact"], f.get("source", ""), now) for f in facts],
        )


def get_all_facts() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT category, fact, timestamp FROM facts ORDER BY timestamp DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def build_knowledge_summary() -> str:
    """Condense profile + facts into a single text block injected into every prompt."""
    profile = get_profile()
    facts = get_all_facts()

    lines: list[str] = ["## Ce que je sais de toi\n"]

    if profile:
        lines.append("### Profil")
        for k, v in profile.items():
            lines.append(f"- **{k}** : {v}")
        lines.append("")

    if facts:
        by_cat: dict[str, list[str]] = {}
        for f in facts:
            by_cat.setdefault(f["category"], []).append(f["fact"])
        lines.append("### Faits appris")
        for cat, items in by_cat.items():
            lines.append(f"**{cat}**")
            seen: set[str] = set()
            for item in items:
                if item not in seen:
                    lines.append(f"  - {item}")
                    seen.add(item)
        lines.append("")

    if len(lines) == 1:
        return ""

    return "\n".join(lines)

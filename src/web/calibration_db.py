"""
calibration_db.py — Persistencia SQLite de los ejemplos de calibración
del profesor, indexados por pregunta.

Esquema:
    examples(id, question, subject, answer, score, created_at)

Solo usa la stdlib (sqlite3) — sin ORM, sin migraciones.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "calibration.db"


def _init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS examples (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                question    TEXT NOT NULL,
                subject     TEXT NOT NULL DEFAULT '',
                answer      TEXT NOT NULL,
                score       REAL NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_examples_question ON examples(question)")
        conn.commit()


@contextmanager
def _conn():
    _init_db()
    c = sqlite3.connect(_DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


def add_example(question: str, subject: str, answer: str, score: float) -> Dict[str, Any]:
    q = question.strip()
    a = answer.strip()
    if not q or not a:
        raise ValueError("question y answer son obligatorios")
    if not (0 <= float(score) <= 10):
        raise ValueError("score debe estar entre 0 y 10")

    # UTC sin offset, manteniendo el formato previo (utcnow() está deprecado).
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO examples (question, subject, answer, score, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (q, subject or "", a, float(score), now),
        )
        c.commit()
        new_id = cur.lastrowid
    return {
        "id": new_id, "question": q, "subject": subject or "",
        "answer": a, "score": float(score), "created_at": now,
    }


def list_examples(question: str | None = None) -> List[Dict[str, Any]]:
    with _conn() as c:
        if question:
            rows = c.execute(
                "SELECT * FROM examples WHERE question = ? ORDER BY created_at DESC",
                (question.strip(),),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM examples ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
    return [dict(r) for r in rows]


def list_questions() -> List[Dict[str, Any]]:
    """Distintas preguntas con cuántos ejemplos hay para cada una."""
    with _conn() as c:
        rows = c.execute(
            "SELECT question, subject, COUNT(*) AS n, MAX(created_at) AS last "
            "FROM examples GROUP BY question, subject ORDER BY last DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_example(example_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM examples WHERE id = ?", (example_id,))
        c.commit()
        return cur.rowcount > 0


def delete_question(question: str) -> int:
    with _conn() as c:
        cur = c.execute("DELETE FROM examples WHERE question = ?", (question.strip(),))
        c.commit()
        return cur.rowcount

"""
templates_db.py — SQLite para plantillas de examen reutilizables y los
gradings (correcciones aplicadas a cada alumno).

Esquema:
    exam_templates(id, name, subject, education_level, structure_json,
                   points_per_cell, created_at)
    template_gradings(id, template_id, student_name, extracted_json,
                      grade_result_json, score_over_10, created_at)

structure_json contiene la tabla con celdas tipadas como:
    {"role": "context", "text": "..."}     # pre-impreso, no se evalúa
    {"role": "evaluable", "correct": "..."} # hueco que el alumno rellena
    {"role": "none"}                        # no aplica (---)
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "calibration.db"


def _init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exam_templates (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT NOT NULL,
                subject          TEXT NOT NULL DEFAULT '',
                education_level  TEXT NOT NULL DEFAULT '',
                structure_json   TEXT NOT NULL,
                points_per_cell  REAL NOT NULL DEFAULT 1.0,
                created_at       TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS template_gradings (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id       INTEGER NOT NULL,
                student_name      TEXT NOT NULL,
                extracted_json    TEXT NOT NULL,
                grade_result_json TEXT NOT NULL,
                score_over_10     REAL NOT NULL,
                created_at        TEXT NOT NULL,
                FOREIGN KEY (template_id) REFERENCES exam_templates(id) ON DELETE CASCADE
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_gradings_template ON template_gradings(template_id)"
        )
        conn.commit()


@contextmanager
def _conn():
    _init_db()
    c = sqlite3.connect(_DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
    finally:
        c.close()


def _row_to_template(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "subject": row["subject"],
        "education_level": row["education_level"],
        "structure": json.loads(row["structure_json"]),
        "points_per_cell": row["points_per_cell"],
        "created_at": row["created_at"],
    }


def _row_to_grading(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "template_id": row["template_id"],
        "student_name": row["student_name"],
        "extracted": json.loads(row["extracted_json"]),
        "grade_result": json.loads(row["grade_result_json"]),
        "score_over_10": row["score_over_10"],
        "created_at": row["created_at"],
    }


# ── Templates CRUD ───────────────────────────────────────────────────────────

def create_template(
    name: str, subject: str, education_level: str,
    structure: Dict[str, Any], points_per_cell: float = 1.0,
) -> Dict[str, Any]:
    if not name.strip():
        raise ValueError("name es obligatorio")
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO exam_templates (name, subject, education_level, "
            "structure_json, points_per_cell, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name.strip(), subject or "", education_level or "",
             json.dumps(structure, ensure_ascii=False),
             float(points_per_cell), now),
        )
        c.commit()
        new_id = cur.lastrowid
    return get_template(new_id)


def list_templates() -> List[Dict[str, Any]]:
    """Lista plantillas con stats agregadas de gradings."""
    with _conn() as c:
        rows = c.execute("""
            SELECT t.*,
                   (SELECT COUNT(*) FROM template_gradings g WHERE g.template_id = t.id) AS gradings_count,
                   (SELECT ROUND(AVG(g.score_over_10), 2) FROM template_gradings g WHERE g.template_id = t.id) AS gradings_mean
            FROM exam_templates t
            ORDER BY t.created_at DESC
        """).fetchall()
    out = []
    for r in rows:
        item = _row_to_template(r)
        item["gradings_count"] = r["gradings_count"] or 0
        item["gradings_mean"] = r["gradings_mean"]
        out.append(item)
    return out


def get_template(template_id: int) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM exam_templates WHERE id = ?", (template_id,)
        ).fetchone()
    return _row_to_template(row) if row else None


def update_template(template_id: int, **fields) -> Optional[Dict[str, Any]]:
    allowed = {"name", "subject", "education_level", "structure", "points_per_cell"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_template(template_id)
    if "structure" in updates:
        updates["structure_json"] = json.dumps(updates.pop("structure"), ensure_ascii=False)
    cols = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [template_id]
    with _conn() as c:
        c.execute(f"UPDATE exam_templates SET {cols} WHERE id = ?", vals)
        c.commit()
    return get_template(template_id)


def delete_template(template_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM exam_templates WHERE id = ?", (template_id,))
        c.commit()
        return cur.rowcount > 0


# ── Gradings ────────────────────────────────────────────────────────────────

def add_grading(
    template_id: int, student_name: str,
    extracted: Dict[str, Any], grade_result: Dict[str, Any],
) -> Dict[str, Any]:
    if not student_name.strip():
        raise ValueError("student_name es obligatorio")
    score = float(grade_result.get("score_over_10", 0.0))
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO template_gradings (template_id, student_name, "
            "extracted_json, grade_result_json, score_over_10, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (template_id, student_name.strip(),
             json.dumps(extracted, ensure_ascii=False),
             json.dumps(grade_result, ensure_ascii=False),
             score, now),
        )
        c.commit()
        new_id = cur.lastrowid
    with _conn() as c:
        row = c.execute("SELECT * FROM template_gradings WHERE id = ?", (new_id,)).fetchone()
    return _row_to_grading(row)


def list_gradings(template_id: int) -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM template_gradings WHERE template_id = ? "
            "ORDER BY created_at DESC",
            (template_id,),
        ).fetchall()
    return [_row_to_grading(r) for r in rows]


def delete_grading(grading_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM template_gradings WHERE id = ?", (grading_id,))
        c.commit()
        return cur.rowcount > 0


def template_stats(template_id: int) -> Dict[str, Any]:
    """Stats agregadas sobre todos los gradings de la plantilla."""
    gradings = list_gradings(template_id)
    if not gradings:
        return {"count": 0, "mean": 0, "median": 0, "min": 0, "max": 0, "top_errors": []}

    import statistics
    scores = [g["score_over_10"] for g in gradings]

    # Top errores: contar conceptos/celdas con verdict != correct
    error_counter: Dict[str, int] = {}
    for g in gradings:
        for cell in g["grade_result"].get("cells", []):
            if cell.get("verdict") in ("wrong", "blank"):
                key = f"row{cell['row']}/col{cell['col']}: {cell.get('correct', '?')}"
                error_counter[key] = error_counter.get(key, 0) + 1

    top_errors = sorted(error_counter.items(), key=lambda kv: -kv[1])[:10]

    return {
        "count": len(scores),
        "mean": round(statistics.mean(scores), 2),
        "median": round(statistics.median(scores), 2),
        "min": round(min(scores), 2),
        "max": round(max(scores), 2),
        "stdev": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0.0,
        "top_errors": [{"item": k, "count": v, "total": len(gradings)} for k, v in top_errors],
    }

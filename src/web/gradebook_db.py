"""
gradebook_db.py — Cuaderno del profesor en SQLite.

Modela el día a día de una clase real:
    classes  (clase/grupo: "1º Bach B", asignatura, curso académico)
      └─ students (alumnos de esa clase)
      └─ exams    (exámenes de esa clase: título, fecha, y la rúbrica con la
                   que se corrige, guardada como JSON)
            └─ grades (una nota por alumno y examen, con el detalle del grader)

Pensado para que un profesor con 30 alumnos pueda: dar de alta la clase y el
listado, crear un examen con su rúbrica, corregir las 30 respuestas de golpe y
que las notas queden guardadas, fechadas y consultables.

Solo stdlib (sqlite3). Claves foráneas con ON DELETE CASCADE.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "gradebook.db"


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def _init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                subject        TEXT NOT NULL DEFAULT '',
                academic_year  TEXT NOT NULL DEFAULT '',
                created_at     TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id    INTEGER NOT NULL,
                name        TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id     INTEGER NOT NULL,
                title        TEXT NOT NULL,
                subject      TEXT NOT NULL DEFAULT '',
                exam_date    TEXT NOT NULL DEFAULT '',
                rubric_json  TEXT NOT NULL DEFAULT '{}',
                created_at   TEXT NOT NULL,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id     INTEGER NOT NULL,
                student_id  INTEGER NOT NULL,
                score       REAL NOT NULL,
                answer      TEXT NOT NULL DEFAULT '',
                detail_json TEXT NOT NULL DEFAULT '{}',
                graded_at   TEXT NOT NULL,
                FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE (exam_id, student_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_students_class ON students(class_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_exams_class ON exams(class_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_grades_exam ON grades(exam_id)")
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


# ── Clases ───────────────────────────────────────────────────────────────────

def create_class(name: str, subject: str = "", academic_year: str = "") -> Dict[str, Any]:
    if not name.strip():
        raise ValueError("El nombre de la clase es obligatorio")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO classes (name, subject, academic_year, created_at) VALUES (?, ?, ?, ?)",
            (name.strip(), subject.strip(), academic_year.strip(), _now()),
        )
        c.commit()
        return get_class(cur.lastrowid)


def list_classes() -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute("""
            SELECT cl.*,
                   (SELECT COUNT(*) FROM students s WHERE s.class_id = cl.id) AS students_count,
                   (SELECT COUNT(*) FROM exams e WHERE e.class_id = cl.id) AS exams_count
            FROM classes cl ORDER BY cl.created_at DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_class(class_id: int) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
    return dict(row) if row else None


def delete_class(class_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM classes WHERE id = ?", (class_id,))
        c.commit()
        return cur.rowcount > 0


# ── Alumnos ──────────────────────────────────────────────────────────────────

def add_student(class_id: int, name: str) -> Dict[str, Any]:
    if not name.strip():
        raise ValueError("El nombre del alumno es obligatorio")
    if get_class(class_id) is None:
        raise ValueError("La clase no existe")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO students (class_id, name, created_at) VALUES (?, ?, ?)",
            (class_id, name.strip(), _now()),
        )
        c.commit()
        row = c.execute("SELECT * FROM students WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def add_students_bulk(class_id: int, names: List[str]) -> List[Dict[str, Any]]:
    """Alta de varios alumnos de golpe (pegar el listado de la clase)."""
    out = []
    for name in names:
        if name.strip():
            out.append(add_student(class_id, name))
    return out


def list_students(class_id: int) -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM students WHERE class_id = ? ORDER BY name COLLATE NOCASE",
            (class_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_student(student_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM students WHERE id = ?", (student_id,))
        c.commit()
        return cur.rowcount > 0


# ── Exámenes ─────────────────────────────────────────────────────────────────

def create_exam(
    class_id: int, title: str, subject: str = "",
    exam_date: str = "", rubric: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not title.strip():
        raise ValueError("El título del examen es obligatorio")
    if get_class(class_id) is None:
        raise ValueError("La clase no existe")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO exams (class_id, title, subject, exam_date, rubric_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (class_id, title.strip(), subject.strip(), exam_date.strip(),
             json.dumps(rubric or {}, ensure_ascii=False), _now()),
        )
        c.commit()
        return get_exam(cur.lastrowid)


def list_exams(class_id: int) -> List[Dict[str, Any]]:
    with _conn() as c:
        rows = c.execute("""
            SELECT e.*,
                   (SELECT COUNT(*) FROM grades g WHERE g.exam_id = e.id) AS graded_count,
                   (SELECT ROUND(AVG(g.score), 2) FROM grades g WHERE g.exam_id = e.id) AS mean_score
            FROM exams e WHERE e.class_id = ? ORDER BY e.exam_date DESC, e.created_at DESC
        """, (class_id,)).fetchall()
    out = []
    for r in rows:
        item = _row_to_exam(r)
        item["graded_count"] = r["graded_count"] or 0
        item["mean_score"] = r["mean_score"]
        out.append(item)
    return out


def _row_to_exam(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"], "class_id": row["class_id"], "title": row["title"],
        "subject": row["subject"], "exam_date": row["exam_date"],
        "rubric": json.loads(row["rubric_json"]), "created_at": row["created_at"],
    }


def get_exam(exam_id: int) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute("SELECT * FROM exams WHERE id = ?", (exam_id,)).fetchone()
    return _row_to_exam(row) if row else None


def delete_exam(exam_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
        c.commit()
        return cur.rowcount > 0


# ── Notas ────────────────────────────────────────────────────────────────────

def upsert_grade(
    exam_id: int, student_id: int, score: float,
    answer: str = "", detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Guarda (o reemplaza) la nota de un alumno en un examen."""
    with _conn() as c:
        c.execute("""
            INSERT INTO grades (exam_id, student_id, score, answer, detail_json, graded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(exam_id, student_id) DO UPDATE SET
                score = excluded.score,
                answer = excluded.answer,
                detail_json = excluded.detail_json,
                graded_at = excluded.graded_at
        """, (exam_id, student_id, float(score), answer,
              json.dumps(detail or {}, ensure_ascii=False), _now()))
        c.commit()
        row = c.execute(
            "SELECT * FROM grades WHERE exam_id = ? AND student_id = ?",
            (exam_id, student_id),
        ).fetchone()
    return _row_to_grade(row)


def _row_to_grade(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"], "exam_id": row["exam_id"], "student_id": row["student_id"],
        "score": row["score"], "answer": row["answer"],
        "detail": json.loads(row["detail_json"]), "graded_at": row["graded_at"],
    }


def list_grades(exam_id: int) -> List[Dict[str, Any]]:
    """Notas del examen con el nombre del alumno (left join: incluye no corregidos)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT s.id AS student_id, s.name AS student_name,
                   g.id AS grade_id, g.score, g.answer, g.detail_json, g.graded_at
            FROM students s
            JOIN exams e ON e.id = ?
            LEFT JOIN grades g ON g.student_id = s.id AND g.exam_id = e.id
            WHERE s.class_id = e.class_id
            ORDER BY s.name COLLATE NOCASE
        """, (exam_id,)).fetchall()
    out = []
    for r in rows:
        out.append({
            "student_id": r["student_id"], "student_name": r["student_name"],
            "grade_id": r["grade_id"],
            "score": r["score"],
            "answer": r["answer"] or "",
            "detail": json.loads(r["detail_json"]) if r["detail_json"] else {},
            "graded_at": r["graded_at"],
            "graded": r["grade_id"] is not None,
        })
    return out


def grades_for_student(student_id: int) -> List[Dict[str, Any]]:
    """Historial de notas de un alumno en todos sus exámenes (boletín)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT g.score, g.graded_at, e.id AS exam_id, e.title, e.subject, e.exam_date
            FROM grades g JOIN exams e ON e.id = g.exam_id
            WHERE g.student_id = ? ORDER BY e.exam_date DESC, g.graded_at DESC
        """, (student_id,)).fetchall()
    return [dict(r) for r in rows]


def exam_stats(exam_id: int) -> Dict[str, Any]:
    """Estadísticas de la clase para un examen."""
    import statistics
    rows = [g for g in list_grades(exam_id) if g["graded"]]
    scores = [g["score"] for g in rows]
    n_total = len(list_grades(exam_id))
    if not scores:
        return {"count": 0, "pending": n_total, "mean": 0, "median": 0,
                "min": 0, "max": 0, "stdev": 0, "pass_count": 0, "fail_count": 0,
                "histogram": {"labels": [], "values": []}}

    bands = list(range(11))  # 0..10
    histogram = [0] * (len(bands) - 1)
    for s in scores:
        histogram[min(int(s), len(histogram) - 1)] += 1

    return {
        "count": len(scores),
        "pending": n_total - len(scores),
        "mean": round(statistics.mean(scores), 2),
        "median": round(statistics.median(scores), 2),
        "min": round(min(scores), 2),
        "max": round(max(scores), 2),
        "stdev": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0.0,
        "pass_count": sum(1 for s in scores if s >= 5),
        "fail_count": sum(1 for s in scores if s < 5),
        "histogram": {
            "labels": [f"{bands[i]}-{bands[i+1]}" for i in range(len(histogram))],
            "values": histogram,
        },
    }

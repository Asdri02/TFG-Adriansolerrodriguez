"""
Tests de los endpoints nuevos:
  - /api/grade_numeric  (Mates/Física determinista + 2ª opinión LLM opcional)
  - /api/grade_writing  (Inglés/Lengua, juez LLM con rúbrica — mockeado)
"""

from __future__ import annotations

import json


# ── /api/grade_numeric ────────────────────────────────────────────────────────

def test_grade_numeric_math_correcto(client):
    r = client.post("/api/grade_numeric", json={
        "student_answer": "Despejo 2x = -6, x = -3", "expected": "x = -3", "kind": "math",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["correct"] is True
    assert data["score_over_10"] == 10.0


def test_grade_numeric_math_conclusion_erronea(client):
    """El caso que el grader semántico aprobaba por error."""
    r = client.post("/api/grade_numeric", json={
        "student_answer": "x = -3... no, en realidad x = 3", "expected": "x = -3", "kind": "math",
    })
    data = r.json()
    assert data["correct"] is False
    assert data["score_over_10"] == 0.0


def test_grade_numeric_physics_valor_unidad(client):
    r = client.post("/api/grade_numeric", json={
        "student_answer": "a = 9.81 m/s^2", "expected": "9.8 m/s^2", "kind": "physics",
    })
    assert r.json()["correct"] is True


def test_grade_numeric_physics_unidad_mal_credito_parcial(client):
    r = client.post("/api/grade_numeric", json={
        "student_answer": "9.8 m/s", "expected": "9.8 m/s^2", "kind": "physics",
    })
    assert r.json()["score_over_10"] == 6.0


def test_grade_numeric_kind_invalido_da_400(client):
    r = client.post("/api/grade_numeric", json={
        "student_answer": "x=1", "expected": "x=1", "kind": "quimica",
    })
    assert r.status_code == 400


def test_grade_numeric_sin_esperado_da_400(client):
    r = client.post("/api/grade_numeric", json={
        "student_answer": "x=1", "expected": "  ", "kind": "math",
    })
    assert r.status_code == 400


def test_grade_numeric_segunda_opinion_llm(client, fake_claude):
    """Con with_llm_opinion=True se adjunta la corrección paso a paso del LLM."""
    fake_claude.set_text(json.dumps({
        "score": 7.0, "steps": [{"name": "planteamiento", "ok": True,
                                  "points_obtained": 7, "points_max": 10, "comment": "bien"}],
        "carry_through_note": "", "summary": "Procedimiento correcto, error de cuenta.",
    }))
    r = client.post("/api/grade_numeric", json={
        "student_answer": "2x=-6 así que x=3", "expected": "x = -3", "kind": "math",
        "question": "Resuelve 2x+6=0", "with_llm_opinion": True,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["correct"] is False          # el resultado determinista falla
    assert data["score_over_10"] == 0.0
    assert "llm_opinion" in data              # pero hay 2ª opinión
    assert data["llm_opinion"]["score"] == 7.0


def test_grade_numeric_segunda_opinion_sin_api_no_rompe(client, fake_claude):
    """Si el LLM falla (p.ej. sin API key), se anota el error pero el endpoint responde."""
    fake_claude.set_exception(RuntimeError("sin api key"))
    r = client.post("/api/grade_numeric", json={
        "student_answer": "x = -3", "expected": "x = -3", "kind": "math",
        "with_llm_opinion": True,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["correct"] is True
    assert "error" in data["llm_opinion"]


# ── /api/grade_writing ────────────────────────────────────────────────────────

def _writing_response():
    return json.dumps({
        "criteria": [
            {"id": "task", "score": 2.0, "max": 2.5, "comment": "cumple la tarea"},
            {"id": "grammar", "score": 1.5, "max": 2.5, "comment": "algunos errores"},
            {"id": "vocabulary", "score": 2.0, "max": 2.5, "comment": "buen léxico"},
            {"id": "coherence", "score": 2.0, "max": 2.5, "comment": "bien cohesionado"},
        ],
        "feedback": "Buen texto con fallos gramaticales menores.",
    })


def test_grade_writing_ingles(client, fake_claude):
    fake_claude.set_text(_writing_response())
    r = client.post("/api/grade_writing", json={
        "question": "Write about your last holiday.",
        "student_answer": "Last summer I went to Italy with my family...",
        "subject": "ingles",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 7.5
    assert data["total_max"] == 10.0
    assert data["score_over_10"] == 7.5
    assert len(data["criteria"]) == 4
    assert data["method"] == "llm_rubric"
    assert "warning" in data


def test_grade_writing_escala_a_10(client, fake_claude):
    """Si la rúbrica no suma 10, la nota se reescala a 0-10."""
    fake_claude.set_text(json.dumps({
        "criteria": [
            {"id": "a", "score": 3.0, "max": 3.0},
            {"id": "b", "score": 1.0, "max": 2.0},
        ],
        "feedback": "ok",
    }))
    r = client.post("/api/grade_writing", json={
        "question": "Comente el texto.", "student_answer": "Mi comentario...",
        "criteria": [{"id": "a", "label": "Contenido", "max": 3.0},
                     {"id": "b", "label": "Forma", "max": 2.0}],
    })
    data = r.json()
    assert data["total"] == 4.0
    assert data["total_max"] == 5.0
    assert data["score_over_10"] == 8.0     # 4/5 * 10


def test_grade_writing_lengua_por_defecto(client, fake_claude):
    fake_claude.set_text(_writing_response())
    r = client.post("/api/grade_writing", json={
        "question": "Comente el tema del texto.",
        "student_answer": "El texto trata sobre...", "subject": "lengua",
    })
    assert r.status_code == 200


def test_grade_writing_sin_respuesta_da_400(client):
    r = client.post("/api/grade_writing", json={
        "question": "x", "student_answer": "   ", "subject": "ingles",
    })
    assert r.status_code == 400


def test_grade_writing_subject_desconocido_da_400(client):
    r = client.post("/api/grade_writing", json={
        "question": "x", "student_answer": "algo", "subject": "biologia",
    })
    assert r.status_code == 400


def test_grade_writing_error_llm_da_502(client, fake_claude):
    fake_claude.set_exception(RuntimeError("down"))
    r = client.post("/api/grade_writing", json={
        "question": "x", "student_answer": "algo", "subject": "ingles",
    })
    assert r.status_code == 502

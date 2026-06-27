"""
Tests de la BD de calibración (CRUD por la API) y del endpoint
/api/calibrate_grade (con Claude mockeado).
"""

from __future__ import annotations

import json


# ── CRUD de ejemplos ─────────────────────────────────────────────────────────

def test_calibration_examples_vacio_al_inicio(client):
    resp = client.get("/api/calibration/examples")
    assert resp.status_code == 200
    assert resp.json() == []


def test_calibration_add_list_delete(client):
    add = client.post("/api/calibration/examples", json={
        "question": "¿Qué es la mitocondria?",
        "subject": "Biología",
        "answer": "El orgánulo de la energía.",
        "score": 7.5,
    })
    assert add.status_code == 200
    ex = add.json()
    assert ex["id"] >= 1
    assert ex["score"] == 7.5

    listed = client.get("/api/calibration/examples").json()
    assert len(listed) == 1

    # filtrado por pregunta
    filtered = client.get(
        "/api/calibration/examples",
        params={"question": "¿Qué es la mitocondria?"},
    ).json()
    assert len(filtered) == 1

    deleted = client.delete(f"/api/calibration/examples/{ex['id']}")
    assert deleted.status_code == 200
    assert client.get("/api/calibration/examples").json() == []


def test_calibration_delete_inexistente_da_404(client):
    resp = client.delete("/api/calibration/examples/9999")
    assert resp.status_code == 404


def test_calibration_score_fuera_de_rango_da_400(client):
    resp = client.post("/api/calibration/examples", json={
        "question": "P", "answer": "R", "score": 11,
    })
    assert resp.status_code == 400


def test_calibration_answer_vacio_da_400(client):
    resp = client.post("/api/calibration/examples", json={
        "question": "P", "answer": "   ", "score": 5,
    })
    assert resp.status_code == 400


def test_calibration_questions_agrupa(client):
    for i in range(3):
        client.post("/api/calibration/examples", json={
            "question": "¿Qué es la mitocondria?",
            "subject": "Biología",
            "answer": f"respuesta {i}",
            "score": 5 + i,
        })
    client.post("/api/calibration/examples", json={
        "question": "¿Qué es la fotosíntesis?",
        "subject": "Biología", "answer": "otra", "score": 6,
    })
    questions = client.get("/api/calibration/questions").json()
    assert len(questions) == 2
    mito = next(q for q in questions if q["question"] == "¿Qué es la mitocondria?")
    assert mito["n"] == 3


# ── /api/calibrate_grade (Claude mockeado) ───────────────────────────────────

def test_calibrate_grade_combina_determinista_y_llm(client, fake_claude, mitocondria_reference):
    fake_claude.set_text(json.dumps({"score": 8.0, "reasoning": "buena cobertura"}))
    resp = client.post("/api/calibrate_grade", json={
        "reference": mitocondria_reference,
        "student_answer": "La mitocondria produce energía ATP en la respiración celular.",
        "examples": [{"answer": "energía y ATP", "score": 7.0}],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["score_llm"] == 8.0
    assert "score_grader" in data
    assert data["delta"] == round(8.0 - data["score_grader"], 2)
    assert data["examples_used"] == 1
    assert data["reasoning"] == "buena cobertura"


def test_calibrate_grade_sin_ejemplos_da_400(client, mitocondria_reference):
    resp = client.post("/api/calibrate_grade", json={
        "reference": mitocondria_reference,
        "student_answer": "algo",
        "examples": [],
    })
    assert resp.status_code == 400


def test_calibrate_grade_limpia_fences_de_markdown(client, fake_claude, mitocondria_reference):
    fake_claude.set_text("```json\n{\"score\": 6.5, \"reasoning\": \"ok\"}\n```")
    resp = client.post("/api/calibrate_grade", json={
        "reference": mitocondria_reference,
        "student_answer": "respuesta",
        "examples": [{"answer": "x", "score": 5}],
    })
    assert resp.status_code == 200
    assert resp.json()["score_llm"] == 6.5


def test_calibrate_grade_error_de_claude_da_502(client, fake_claude, mitocondria_reference):
    fake_claude.set_exception(RuntimeError("boom"))
    resp = client.post("/api/calibrate_grade", json={
        "reference": mitocondria_reference,
        "student_answer": "respuesta",
        "examples": [{"answer": "x", "score": 5}],
    })
    assert resp.status_code == 502


def test_calibrate_grade_json_invalido_da_502(client, fake_claude, mitocondria_reference):
    fake_claude.set_text("esto no es json")
    resp = client.post("/api/calibrate_grade", json={
        "reference": mitocondria_reference,
        "student_answer": "respuesta",
        "examples": [{"answer": "x", "score": 5}],
    })
    assert resp.status_code == 502


# ── /api/calibrate_deterministic (sin LLM) ───────────────────────────────────

def _cal_body(student, examples):
    return {
        "reference": {
            "question": "¿Qué es la mitocondria?",
            "subject": "Biología", "ideal_answer": "Orgánulo de la respiración celular que produce ATP.",
            "key_concepts": [{"concept": "respiración celular", "weight": 0.5},
                             {"concept": "ATP", "weight": 0.5}],
        },
        "student_answer": student,
        "examples": examples,
    }


def test_calibrate_deterministic_ajusta_escala(client):
    body = _cal_body(
        "La mitocondria produce ATP en la respiración celular.",
        [{"answer": "Orgánulo de la respiración celular que produce ATP.", "score": 9.0},
         {"answer": "Produce energía en la célula.", "score": 6.0},
         {"answer": "Es algo de la célula.", "score": 4.0},
         {"answer": "No lo sé.", "score": 2.0}],
    )
    resp = client.post("/api/calibrate_deterministic", json=body)
    assert resp.status_code == 200
    data = resp.json()
    for k in ("score_grader", "score_calibrated", "delta", "method", "mapping",
              "mae_examples_before", "mae_examples_after", "fit"):
        assert k in data
    assert 0.0 <= data["score_calibrated"] <= 10.0
    assert len(data["fit"]) == 4
    # la calibración debe acercar la nota de los ejemplos a la del profesor
    assert data["mae_examples_after"] <= data["mae_examples_before"]


def test_calibrate_deterministic_pocos_ejemplos_da_400(client):
    body = _cal_body("algo", [{"answer": "x", "score": 5.0}])
    resp = client.post("/api/calibrate_deterministic", json=body)
    assert resp.status_code == 400

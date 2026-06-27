"""
Tests de los endpoints deterministas de corrección:
  /api/grade, /api/cases, /api/grade_case, /api/validate, /api/grade_batch.

Ninguno necesita Claude ni Tesseract.
"""

from __future__ import annotations


# ── /api/grade ───────────────────────────────────────────────────────────────

def test_grade_respuesta_completa(client, mitocondria_reference):
    resp = client.post("/api/grade", json={
        "student_answer": (
            "La mitocondria es el orgánulo que produce energía en forma de ATP "
            "mediante la respiración celular."
        ),
        "reference": mitocondria_reference,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["score_over_10"] >= 8.0
    assert set(["orgánulo", "energía", "ATP", "respiración celular"]).issubset(
        set(data["detected_concepts"])
    )
    assert "reference" in data
    assert data["antipatterns_hit"] == []


def test_grade_respuesta_incorrecta_puntua_bajo(client, mitocondria_reference):
    resp = client.post("/api/grade", json={
        "student_answer": "La mitocondria almacena el material genético de la célula.",
        "reference": mitocondria_reference,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["score_over_10"] <= 3.0
    assert "ATP" in data["missing_concepts"]


def test_grade_estructura_de_respuesta_completa(client, mitocondria_reference):
    """El payload de respuesta debe traer todas las métricas que el front usa."""
    resp = client.post("/api/grade", json={
        "student_answer": "produce energía ATP",
        "reference": mitocondria_reference,
    })
    data = resp.json()
    for key in ("score_over_10", "concept_ratio", "similarity_ratio",
                "length_penalty", "detected_concepts", "partial_concepts",
                "missing_concepts", "bonus_hits", "feedback"):
        assert key in data, f"falta {key} en la respuesta del grader"


def test_grade_falta_campo_requerido_da_422(client):
    resp = client.post("/api/grade", json={"student_answer": "algo"})
    assert resp.status_code == 422  # validación de pydantic


def test_grade_bonus_terms_suben_nota(client, mitocondria_reference):
    """Un término bonus presente en la respuesta debe sumar al ratio final."""
    base = client.post("/api/grade", json={
        "student_answer": "La mitocondria produce energía.",
        "reference": mitocondria_reference,
    }).json()["score_over_10"]

    ref_bonus = dict(mitocondria_reference)
    ref_bonus["bonus_terms"] = [{"term": "energía", "weight": 0.3}]
    boosted = client.post("/api/grade", json={
        "student_answer": "La mitocondria produce energía.",
        "reference": ref_bonus,
    }).json()
    assert boosted["score_over_10"] >= base
    assert any(b["term"] == "energía" for b in boosted["bonus_hits"])


# ── /api/cases ───────────────────────────────────────────────────────────────

def test_list_cases_devuelve_los_40(client):
    resp = client.get("/api/cases")
    assert resp.status_code == 200
    cases = resp.json()
    assert len(cases) == 40
    first = cases[0]
    for key in ("id", "topic", "desc", "subject", "question",
                "ideal_answer", "key_concepts", "student_answer",
                "nota_min", "nota_max"):
        assert key in first


# ── /api/grade_case ──────────────────────────────────────────────────────────

def test_grade_case_usa_respuesta_del_caso(client):
    resp = client.post("/api/grade_case", json={"case_id": 1})
    assert resp.status_code == 200
    # El caso 1 es la respuesta completa de mitocondria → nota alta
    assert resp.json()["score_over_10"] >= 8.0


def test_grade_case_acepta_respuesta_custom(client):
    resp = client.post("/api/grade_case", json={
        "case_id": 1,
        "student_answer": "no tengo ni idea",
    })
    assert resp.status_code == 200
    assert resp.json()["score_over_10"] < 5.0


def test_grade_case_inexistente_da_404(client):
    resp = client.post("/api/grade_case", json={"case_id": 9999})
    assert resp.status_code == 404


# ── /api/validate ────────────────────────────────────────────────────────────

def test_validate_resumen_global(client):
    resp = client.get("/api/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 40
    assert data["passed"] + data["expected_fails"] + data["unexpected_fails"] == 40
    assert 0.0 <= data["conformant_pct"] <= 100.0
    assert "per_subject" in data and "per_topic" in data
    assert len(data["cases"]) == 40


def test_validate_no_tiene_fallos_inesperados(client):
    """La suite de validación debe estar calibrada: 0 unexpected_fails."""
    data = client.get("/api/validate").json()
    fallos = [c for c in data["cases"] if c["status"] == "unexpected_fail"]
    assert data["unexpected_fails"] == 0, (
        f"Casos que fallan sin estar marcados como expected_to_fail: "
        f"{[(c['id'], c['desc'], c['score']) for c in fallos]}"
    )


# ── /api/grade_batch ─────────────────────────────────────────────────────────

def test_grade_batch_basico(client, mitocondria_reference):
    resp = client.post("/api/grade_batch", json={
        "reference": mitocondria_reference,
        "answers": [
            {"id": "alumno1", "text": "La mitocondria produce energía ATP en la respiración celular."},
            {"id": "alumno2", "text": "no lo sé"},
            {"id": "alumno3", "text": "El orgánulo de la energía."},
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["count"] == 3
    assert len(data["results"]) == 3
    assert data["stats"]["pass_count"] + data["stats"]["fail_count"] == 3
    assert sum(data["histogram"]["values"]) == 3
    assert len(data["histogram"]["labels"]) == len(data["histogram"]["values"])


def test_grade_batch_ignora_respuestas_vacias(client, mitocondria_reference):
    resp = client.post("/api/grade_batch", json={
        "reference": mitocondria_reference,
        "answers": [
            {"text": "La mitocondria produce energía ATP."},
            {"text": "   "},
            {"text": ""},
        ],
    })
    assert resp.status_code == 200
    assert resp.json()["stats"]["count"] == 1


def test_grade_batch_sin_respuestas_da_400(client, mitocondria_reference):
    resp = client.post("/api/grade_batch", json={
        "reference": mitocondria_reference,
        "answers": [],
    })
    assert resp.status_code == 400


def test_grade_batch_todo_vacio_da_400(client, mitocondria_reference):
    resp = client.post("/api/grade_batch", json={
        "reference": mitocondria_reference,
        "answers": [{"text": "  "}, {"text": ""}],
    })
    assert resp.status_code == 400


# ── /api/correlation (Spearman vs nota humana de referencia) ─────────────────

def test_correlation_estructura_y_rango(client):
    resp = client.get("/api/correlation")
    assert resp.status_code == 200
    data = resp.json()
    # métricas presentes y en rango
    for k in ("n", "spearman", "pearson", "mae", "rmse", "per_question", "points", "note"):
        assert k in data
    assert data["n"] == len(data["points"]) == 30
    assert -1.0 <= data["spearman"] <= 1.0
    assert -1.0 <= data["pearson"] <= 1.0
    assert data["mae"] >= 0.0 and data["rmse"] >= 0.0
    # el sistema debe concordar ALTO con el criterio humano de referencia
    assert data["spearman"] >= 0.8
    # cada punto trae nota humana y del sistema en escala 0-10
    p = data["points"][0]
    assert 0.0 <= p["human"] <= 10.0 and 0.0 <= p["system"] <= 10.0
    assert len(data["per_question"]) == 6

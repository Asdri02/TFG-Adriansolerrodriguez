"""
Tests de los endpoints que delegan en Claude (texto y Vision), todos mockeados:
  /api/generate_reference, /api/explain_grade, /api/grade_steps,
  /api/extract_structured, /api/generate_solutions, /api/templates/from_image.
"""

from __future__ import annotations

import json

import pytest

from ai.models import ReferenceAnswer


# ── /api/generate_reference (mockea reference_db) ────────────────────────────

def test_generate_reference_ok(client, monkeypatch, mitocondria_reference):
    import reference_db

    fake_ref = ReferenceAnswer(
        question="¿Qué es la mitocondria?",
        subject="Biología",
        education_level="Bachillerato",
        expected_answer_type="respuesta_abierta",
        ideal_answer="La mitocondria produce ATP.",
        key_concepts=[{"concept": "ATP", "weight": 1.0}],
        common_mistakes=["confundir con núcleo"],
        confidence=0.9,
    )
    monkeypatch.setattr(reference_db, "get_reference", lambda *a, **k: fake_ref)

    resp = client.post("/api/generate_reference", json={
        "question": "¿Qué es la mitocondria?",
        "subject": "Biología",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ideal_answer"] == "La mitocondria produce ATP."
    assert data["key_concepts"][0]["concept"] == "ATP"
    assert data["confidence"] == 0.9


def test_generate_reference_pregunta_vacia_da_400(client):
    resp = client.post("/api/generate_reference", json={"question": "   "})
    assert resp.status_code == 400


def test_generate_reference_force_invalida_cache(client, monkeypatch):
    import reference_db
    invalidated = {"called": False}

    def fake_invalidate(q):
        invalidated["called"] = True
        return True

    fake_ref = ReferenceAnswer(
        question="P", subject="General", education_level="Bachillerato",
        expected_answer_type="respuesta_abierta", ideal_answer="R",
        key_concepts=[], confidence=0.5,
    )
    monkeypatch.setattr(reference_db, "invalidate", fake_invalidate)
    monkeypatch.setattr(reference_db, "get_reference", lambda *a, **k: fake_ref)

    resp = client.post("/api/generate_reference", json={"question": "P", "force": True})
    assert resp.status_code == 200
    assert invalidated["called"] is True


def test_generate_reference_error_da_502(client, monkeypatch):
    import reference_db

    def boom(*a, **k):
        raise RuntimeError("api caída")

    monkeypatch.setattr(reference_db, "get_reference", boom)
    resp = client.post("/api/generate_reference", json={"question": "P"})
    assert resp.status_code == 502


# ── /api/explain_grade ───────────────────────────────────────────────────────

def test_explain_grade_ok(client, fake_claude, mitocondria_reference):
    fake_claude.set_text("Tu respuesta cubre la mayoría de los conceptos clave.")
    resp = client.post("/api/explain_grade", json={
        "reference": mitocondria_reference,
        "student_answer": "La mitocondria produce ATP.",
        "grade_result": {
            "score_over_10": 7.0,
            "detected_concepts": ["ATP"],
            "partial_concepts": [],
            "missing_concepts": ["respiración celular"],
            "antipatterns_hit": [],
        },
    })
    assert resp.status_code == 200
    assert "conceptos" in resp.json()["explanation"]


def test_explain_grade_error_da_502(client, fake_claude, mitocondria_reference):
    fake_claude.set_exception(RuntimeError("down"))
    resp = client.post("/api/explain_grade", json={
        "reference": mitocondria_reference,
        "student_answer": "x",
        "grade_result": {"score_over_10": 5.0},
    })
    assert resp.status_code == 502


# ── /api/grade_steps (experimental) ──────────────────────────────────────────

def test_grade_steps_ok(client, fake_claude):
    fake_claude.set_text(json.dumps({
        "score": 7.5,
        "steps": [{"name": "Apartado a", "ok": True, "points_obtained": 5,
                   "points_max": 5, "comment": "bien"}],
        "carry_through_note": "",
        "summary": "Procedimiento correcto en su mayoría.",
    }))
    resp = client.post("/api/grade_steps", json={
        "question": "Resuelve 2x + 3 = 7",
        "student_answer": "x = 2",
        "subject": "Matemáticas",
        "max_points": 10,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 7.5
    assert len(data["steps"]) == 1
    assert "experimental_warning" in data


def test_grade_steps_falta_question_da_400(client, fake_claude):
    resp = client.post("/api/grade_steps", json={
        "question": "  ", "student_answer": "x = 2",
    })
    assert resp.status_code == 400


def test_grade_steps_error_da_502(client, fake_claude):
    fake_claude.set_exception(RuntimeError("down"))
    resp = client.post("/api/grade_steps", json={
        "question": "Q", "student_answer": "A",
    })
    assert resp.status_code == 502


# ── /api/extract_structured (Vision) ─────────────────────────────────────────

def test_extract_structured_ok(client, fake_vision):
    fake_vision.set_text(json.dumps({
        "type": "table",
        "headers": ["Fórmula", "Nombre"],
        "rows": [[{"text": "H2O", "kind": "printed"}, {"text": "agua", "kind": "student"}]],
    }))
    resp = client.post(
        "/api/extract_structured",
        files={"image": ("examen.png", b"fakebytes", "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["type"] == "table"


def test_extract_structured_no_imagen_da_400(client, fake_vision):
    resp = client.post(
        "/api/extract_structured",
        files={"image": ("examen.txt", b"x", "text/plain")},
    )
    assert resp.status_code == 400


def test_extract_structured_json_invalido_da_502(client, fake_vision):
    fake_vision.set_text("no soy json")
    resp = client.post(
        "/api/extract_structured",
        files={"image": ("examen.png", b"x", "image/png")},
    )
    assert resp.status_code == 502


def test_extract_structured_estructura_incompleta_da_502(client, fake_vision):
    """Falta la clave 'rows' → sanidad mínima rechaza."""
    fake_vision.set_text(json.dumps({"type": "table"}))
    resp = client.post(
        "/api/extract_structured",
        files={"image": ("examen.png", b"x", "image/png")},
    )
    assert resp.status_code == 502


# ── /api/generate_solutions ──────────────────────────────────────────────────

def test_generate_solutions_ok(client, fake_claude):
    fake_claude.set_text(json.dumps({
        "solutions": [{"row": 0, "col": 1, "correct": "agua"}]
    }))
    resp = client.post("/api/generate_solutions", json={
        "structure": {
            "type": "table",
            "headers": ["Fórmula", "Nombre"],
            "rows": [[{"text": "H2O", "kind": "printed"}, {"text": "[?]", "kind": "student"}]],
        },
        "subject": "Química",
    })
    assert resp.status_code == 200
    assert resp.json()["solutions"][0]["correct"] == "agua"


def test_generate_solutions_error_da_502(client, fake_claude):
    fake_claude.set_exception(RuntimeError("down"))
    resp = client.post("/api/generate_solutions", json={
        "structure": {"type": "table", "rows": []},
    })
    assert resp.status_code == 502


# ── /api/templates/from_image ────────────────────────────────────────────────

def test_templates_from_image_corrected(client, fake_vision):
    """En modo 'corrected', las respuestas del alumno se vuelven las correctas."""
    fake_vision.set_text(json.dumps({
        "type": "table",
        "title": "Formulación",
        "headers": ["Fórmula", "Nombre"],
        "rows": [[{"text": "H2O", "kind": "printed"}, {"text": "agua", "kind": "student"}]],
    }))
    resp = client.post(
        "/api/templates/from_image",
        files={"image": ("examen.png", b"x", "image/png")},
        data={"mode": "corrected", "subject": "Química"},
    )
    assert resp.status_code == 200
    structure = resp.json()["structure"]
    evaluable = structure["rows"][0][1]
    assert evaluable["role"] == "evaluable"
    assert evaluable["correct"] == "agua"


def test_templates_from_image_blank_pide_soluciones(client, fake_vision, monkeypatch):
    """En modo 'blank', se llama a generate_solutions para rellenar las correctas."""
    fake_vision.set_text(json.dumps({
        "type": "table",
        "headers": ["Fórmula", "Nombre"],
        "rows": [[{"text": "H2O", "kind": "printed"}, {"text": "", "kind": "blank"}]],
    }))
    from web import app as app_module
    monkeypatch.setattr(
        app_module, "generate_solutions",
        lambda req: {"solutions": [{"row": 0, "col": 1, "correct": "agua"}]},
    )
    resp = client.post(
        "/api/templates/from_image",
        files={"image": ("examen.png", b"x", "image/png")},
        data={"mode": "blank", "subject": "Química"},
    )
    assert resp.status_code == 200
    assert resp.json()["structure"]["rows"][0][1]["correct"] == "agua"


def test_templates_from_image_blank_avisa_si_falla_generacion(client, fake_vision, monkeypatch):
    """Si la autogeneración de soluciones falla, no aborta: avisa en solutions_warning."""
    fake_vision.set_text(json.dumps({
        "type": "table",
        "headers": ["Fórmula", "Nombre"],
        "rows": [[{"text": "H2O", "kind": "printed"}, {"text": "", "kind": "blank"}]],
    }))
    from web import app as app_module

    def boom(req):
        raise RuntimeError("claude caído")

    monkeypatch.setattr(app_module, "generate_solutions", boom)
    resp = client.post(
        "/api/templates/from_image",
        files={"image": ("examen.png", b"x", "image/png")},
        data={"mode": "blank", "subject": "Química"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["solutions_warning"] is not None
    assert "RuntimeError" in data["solutions_warning"]
    # la celda evaluable queda con correct vacío para rellenar a mano
    assert data["structure"]["rows"][0][1]["correct"] == ""


def test_explain_grade_sin_score_da_400(client, fake_claude, mitocondria_reference):
    """grade_result sin score_over_10 → 400 limpio, no 500."""
    resp = client.post("/api/explain_grade", json={
        "reference": mitocondria_reference,
        "student_answer": "x",
        "grade_result": {"detected_concepts": []},  # falta score_over_10
    })
    assert resp.status_code == 400


def test_templates_from_image_mode_invalido_da_400(client, fake_vision):
    resp = client.post(
        "/api/templates/from_image",
        files={"image": ("examen.png", b"x", "image/png")},
        data={"mode": "loquesea"},
    )
    assert resp.status_code == 400


def test_templates_from_image_no_imagen_da_400(client, fake_vision):
    resp = client.post(
        "/api/templates/from_image",
        files={"image": ("examen.txt", b"x", "text/plain")},
        data={"mode": "blank"},
    )
    assert resp.status_code == 400


# ── /api/verify_answer (mockea ai.verifier.verify_factuality) ────────────────

def test_verify_answer_marca_revision_si_hay_atribucion_erronea(
    client, monkeypatch, mitocondria_reference
):
    """El grader cuenta los conceptos, pero el verificador los marca mal
    atribuidos → needs_review=True y los conflictos se listan."""
    import ai.verifier as verifier

    def fake_verify(question, ideal_answer, key_concepts, student_answer):
        return {
            "contradiction": True,
            "concepts": [
                {"concept": "ATP", "status": "atribucion_erronea", "comment": "es del cloroplasto"},
                {"concept": "respiración celular", "status": "atribucion_erronea", "comment": ""},
            ],
            "flagged": [
                {"concept": "ATP", "status": "atribucion_erronea", "comment": ""},
                {"concept": "respiración celular", "status": "atribucion_erronea", "comment": ""},
            ],
            "advice": "revisar",
            "method": "llm_verifier",
        }

    monkeypatch.setattr(verifier, "verify_factuality", fake_verify)

    resp = client.post("/api/verify_answer", json={
        "student_answer": "La respiración celular y el ATP son cosas del cloroplasto, no de la mitocondria.",
        "reference": mitocondria_reference,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["needs_review"] is True
    # ATP lo había acreditado el grader y el verificador lo marca → es conflicto
    assert any(c["concept"] == "ATP" for c in data["conflicts"])


def test_verify_answer_sin_conflicto_no_pide_revision(
    client, monkeypatch, mitocondria_reference
):
    import ai.verifier as verifier

    def fake_verify(question, ideal_answer, key_concepts, student_answer):
        return {
            "contradiction": False,
            "concepts": [{"concept": "ATP", "status": "correcto", "comment": ""}],
            "flagged": [],
            "advice": "ok",
            "method": "llm_verifier",
        }

    monkeypatch.setattr(verifier, "verify_factuality", fake_verify)

    resp = client.post("/api/verify_answer", json={
        "student_answer": "La mitocondria produce ATP mediante la respiración celular.",
        "reference": mitocondria_reference,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["needs_review"] is False
    assert data["conflicts"] == []


def test_verify_answer_degrada_si_no_hay_llm(client, monkeypatch, mitocondria_reference):
    import ai.verifier as verifier

    def boom(*a, **k):
        raise RuntimeError("verificador LLM no disponible: X")

    monkeypatch.setattr(verifier, "verify_factuality", boom)
    resp = client.post("/api/verify_answer", json={
        "student_answer": "algo", "reference": mitocondria_reference,
    })
    assert resp.status_code == 502

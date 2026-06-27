"""
Tests del CRUD de plantillas de examen, sus gradings y stats.
"""

from __future__ import annotations


def _sample_structure():
    return {
        "type": "table",
        "title": "Formulación química",
        "instructions": "Nombra cada compuesto",
        "headers": ["Fórmula", "Nomenclatura"],
        "rows": [
            [
                {"role": "context", "text": "H2O"},
                {"role": "evaluable", "correct": "agua"},
            ],
            [
                {"role": "context", "text": "CO2"},
                {"role": "evaluable", "correct": "dióxido de carbono"},
            ],
        ],
    }


def _create_template(client, name="Plantilla quimica"):
    return client.post("/api/templates", json={
        "name": name,
        "subject": "Química",
        "education_level": "Bachillerato",
        "structure": _sample_structure(),
        "points_per_cell": 1.0,
    })


# ── CRUD ─────────────────────────────────────────────────────────────────────

def test_templates_list_vacio(client):
    assert client.get("/api/templates").json() == []


def test_template_create_y_get(client):
    created = _create_template(client)
    assert created.status_code == 200
    tpl = created.json()
    assert tpl["id"] >= 1
    assert tpl["name"] == "Plantilla quimica"
    assert tpl["gradings_count"] == 0 if "gradings_count" in tpl else True

    got = client.get(f"/api/templates/{tpl['id']}")
    assert got.status_code == 200
    assert got.json()["structure"]["type"] == "table"


def test_template_get_inexistente_da_404(client):
    assert client.get("/api/templates/9999").status_code == 404


def test_template_update(client):
    tpl = _create_template(client).json()
    upd = client.put(f"/api/templates/{tpl['id']}", json={"name": "Nuevo nombre"})
    assert upd.status_code == 200
    assert upd.json()["name"] == "Nuevo nombre"


def test_template_update_inexistente_da_404(client):
    assert client.put("/api/templates/9999", json={"name": "x"}).status_code == 404


def test_template_delete(client):
    tpl = _create_template(client).json()
    assert client.delete(f"/api/templates/{tpl['id']}").status_code == 200
    assert client.get(f"/api/templates/{tpl['id']}").status_code == 404


def test_template_delete_inexistente_da_404(client):
    assert client.delete("/api/templates/9999").status_code == 404


# ── Gradings y stats ─────────────────────────────────────────────────────────

def test_template_gradings_vacio_y_stats(client):
    tpl = _create_template(client).json()
    assert client.get(f"/api/templates/{tpl['id']}/gradings").json() == []
    stats = client.get(f"/api/templates/{tpl['id']}/stats").json()
    assert stats["count"] == 0
    assert stats["top_errors"] == []


def test_template_grade_image_y_stats(client, fake_vision):
    """
    Flujo completo: crear plantilla → aplicar a una 'imagen' de alumno (Vision
    mockeado) → comprobar grading guardado → stats agregadas.
    """
    tpl = _create_template(client).json()

    # El alumno acierta H2O ("agua") y falla CO2 ("oxígeno")
    fake_vision.set_text("""
    {
      "type": "table",
      "rows": [
        [{"text": "H2O", "kind": "printed"}, {"text": "agua", "kind": "student"}],
        [{"text": "CO2", "kind": "printed"}, {"text": "oxigeno", "kind": "student"}]
      ]
    }
    """)

    resp = client.post(
        f"/api/templates/{tpl['id']}/grade_image",
        files={"image": ("alumno.png", b"fakebytes", "image/png")},
        data={"student_name": "Ana"},
    )
    assert resp.status_code == 200
    grade = resp.json()
    assert grade["student_name"] == "Ana"
    assert grade["max_points"] == 2.0
    assert grade["earned"] == 1.0  # solo agua correcta
    assert grade["score_over_10"] == 5.0

    gradings = client.get(f"/api/templates/{tpl['id']}/gradings").json()
    assert len(gradings) == 1

    stats = client.get(f"/api/templates/{tpl['id']}/stats").json()
    assert stats["count"] == 1
    # CO2/oxigeno es un error → aparece en top_errors
    assert any("dióxido de carbono" in e["item"] for e in stats["top_errors"])


def test_template_grade_image_sin_nombre_da_400(client, fake_vision):
    tpl = _create_template(client).json()
    fake_vision.set_text('{"type": "table", "rows": []}')
    resp = client.post(
        f"/api/templates/{tpl['id']}/grade_image",
        files={"image": ("a.png", b"x", "image/png")},
        data={"student_name": "   "},
    )
    assert resp.status_code == 400


def test_template_grade_image_plantilla_inexistente_da_404(client):
    resp = client.post(
        "/api/templates/9999/grade_image",
        files={"image": ("a.png", b"x", "image/png")},
        data={"student_name": "Ana"},
    )
    assert resp.status_code == 404


def test_template_grade_image_no_imagen_da_400(client, fake_vision):
    tpl = _create_template(client).json()
    resp = client.post(
        f"/api/templates/{tpl['id']}/grade_image",
        files={"image": ("a.txt", b"x", "text/plain")},
        data={"student_name": "Ana"},
    )
    assert resp.status_code == 400


def test_template_grade_image_sin_celdas_evaluables_da_400(client, fake_vision):
    """Plantilla con todas las celdas correct vacías → no hay nada que evaluar."""
    empty_structure = {
        "type": "table", "title": "", "instructions": "", "headers": [],
        "rows": [[{"role": "context", "text": "H2O"}, {"role": "evaluable", "correct": ""}]],
    }
    tpl = client.post("/api/templates", json={
        "name": "Vacia", "subject": "", "education_level": "",
        "structure": empty_structure, "points_per_cell": 1.0,
    }).json()
    fake_vision.set_text('{"type": "table", "rows": [[{"text":"H2O","kind":"printed"},{"text":"agua","kind":"student"}]]}')
    resp = client.post(
        f"/api/templates/{tpl['id']}/grade_image",
        files={"image": ("a.png", b"x", "image/png")},
        data={"student_name": "Ana"},
    )
    assert resp.status_code == 400


def test_delete_grading(client, fake_vision):
    tpl = _create_template(client).json()
    fake_vision.set_text('{"type":"table","rows":[[{"text":"H2O","kind":"printed"},{"text":"agua","kind":"student"}]]}')
    grade = client.post(
        f"/api/templates/{tpl['id']}/grade_image",
        files={"image": ("a.png", b"x", "image/png")},
        data={"student_name": "Ana"},
    ).json()
    gid = grade["grading_id"]
    assert client.delete(f"/api/templates/{tpl['id']}/gradings/{gid}").status_code == 200
    assert client.get(f"/api/templates/{tpl['id']}/gradings").json() == []


def test_delete_grading_inexistente_da_404(client):
    tpl = _create_template(client).json()
    assert client.delete(f"/api/templates/{tpl['id']}/gradings/9999").status_code == 404

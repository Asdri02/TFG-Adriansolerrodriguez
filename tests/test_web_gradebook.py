"""
Tests del Cuaderno del Profesor: clases, alumnos, exámenes y la corrección de
toda la clase de una vez con persistencia de notas.
"""

from __future__ import annotations


def _rubric():
    return {
        "question": "¿Qué es la mitocondria?",
        "subject": "Biología",
        "education_level": "Bachillerato",
        "ideal_answer": "La mitocondria produce energía en forma de ATP mediante la respiración celular.",
        "key_concepts": [
            {"concept": "orgánulo", "weight": 0.2},
            {"concept": "energía", "weight": 0.3},
            {"concept": "ATP", "weight": 0.3},
            {"concept": "respiración celular", "weight": 0.2},
        ],
        "bonus_terms": [],
    }


def _make_class(client, name="1º Bach B"):
    return client.post("/api/gradebook/classes", json={
        "name": name, "subject": "Biología", "academic_year": "2025-2026",
    }).json()


def _add_students(client, class_id, names):
    return client.post(
        f"/api/gradebook/classes/{class_id}/students/bulk", json={"names": names},
    ).json()


def _make_exam(client, class_id, title="Examen Tema 3"):
    return client.post(f"/api/gradebook/classes/{class_id}/exams", json={
        "title": title, "exam_date": "2026-05-20", "subject": "Biología", "rubric": _rubric(),
    }).json()


# ── Clases ───────────────────────────────────────────────────────────────────

def test_classes_vacio(client):
    assert client.get("/api/gradebook/classes").json() == []


def test_create_class_y_listar(client):
    c = _make_class(client)
    assert c["id"] >= 1
    listed = client.get("/api/gradebook/classes").json()
    assert len(listed) == 1
    assert listed[0]["students_count"] == 0
    assert listed[0]["exams_count"] == 0


def test_create_class_sin_nombre_da_400(client):
    assert client.post("/api/gradebook/classes", json={"name": "  "}).status_code == 400


def test_delete_class_cascada(client):
    """Borrar la clase elimina alumnos, exámenes y notas (cascade)."""
    c = _make_class(client)
    students = _add_students(client, c["id"], ["Ana", "Luis"])
    exam = _make_exam(client, c["id"])
    client.post(f"/api/gradebook/exams/{exam['id']}/grade_class", json={
        "answers": [{"student_id": students[0]["id"], "text": "produce energía ATP"}],
    })
    assert client.delete(f"/api/gradebook/classes/{c['id']}").status_code == 200
    assert client.get("/api/gradebook/classes").json() == []
    # el examen ya no existe
    assert client.get(f"/api/gradebook/exams/{exam['id']}").status_code == 404


def test_delete_class_inexistente_da_404(client):
    assert client.delete("/api/gradebook/classes/9999").status_code == 404


# ── Alumnos ──────────────────────────────────────────────────────────────────

def test_add_students_bulk_y_orden_alfabetico(client):
    c = _make_class(client)
    _add_students(client, c["id"], ["Luis", "Ana", "", "  ", "María"])
    students = client.get(f"/api/gradebook/classes/{c['id']}/students").json()
    assert [s["name"] for s in students] == ["Ana", "Luis", "María"]  # ignora vacíos, ordena


def test_add_student_individual(client):
    c = _make_class(client)
    s = client.post(f"/api/gradebook/classes/{c['id']}/students", json={"name": "Pedro"}).json()
    assert s["name"] == "Pedro"
    assert s["class_id"] == c["id"]


def test_add_student_clase_inexistente_da_400(client):
    assert client.post("/api/gradebook/classes/9999/students", json={"name": "X"}).status_code == 400


def test_delete_student(client):
    c = _make_class(client)
    s = _add_students(client, c["id"], ["Ana"])[0]
    assert client.delete(f"/api/gradebook/students/{s['id']}").status_code == 200
    assert client.get(f"/api/gradebook/classes/{c['id']}/students").json() == []


def test_students_clase_inexistente_da_404(client):
    assert client.get("/api/gradebook/classes/9999/students").status_code == 404


# ── Exámenes ─────────────────────────────────────────────────────────────────

def test_create_exam_guarda_rubrica(client):
    c = _make_class(client)
    exam = _make_exam(client, c["id"])
    assert exam["title"] == "Examen Tema 3"
    assert exam["exam_date"] == "2026-05-20"
    assert exam["rubric"]["question"] == "¿Qué es la mitocondria?"
    got = client.get(f"/api/gradebook/exams/{exam['id']}").json()
    assert len(got["rubric"]["key_concepts"]) == 4


def test_list_exams_con_contadores(client):
    c = _make_class(client)
    _make_exam(client, c["id"])
    exams = client.get(f"/api/gradebook/classes/{c['id']}/exams").json()
    assert len(exams) == 1
    assert exams[0]["graded_count"] == 0


def test_delete_exam(client):
    c = _make_class(client)
    exam = _make_exam(client, c["id"])
    assert client.delete(f"/api/gradebook/exams/{exam['id']}").status_code == 200
    assert client.get(f"/api/gradebook/exams/{exam['id']}").status_code == 404


# ── Corregir toda la clase ───────────────────────────────────────────────────

def test_grade_class_corrige_y_persiste(client):
    c = _make_class(client)
    students = _add_students(client, c["id"], ["Ana", "Luis", "María"])
    exam = _make_exam(client, c["id"])

    answers = [
        {"student_id": students[0]["id"],
         "text": "La mitocondria es el orgánulo que produce energía ATP mediante la respiración celular."},
        {"student_id": students[1]["id"], "text": "produce energía"},
        {"student_id": students[2]["id"], "text": "no lo sé"},
    ]
    res = client.post(f"/api/gradebook/exams/{exam['id']}/grade_class", json={"answers": answers})
    assert res.status_code == 200
    data = res.json()
    assert data["graded_count"] == 3
    assert data["stats"]["count"] == 3
    # Ana (respuesta completa) debe sacar más que María (irrelevante)
    by_id = {g["student_id"]: g for g in data["grades"] if g["graded"]}
    assert by_id[students[0]["id"]]["score"] > by_id[students[2]["id"]]["score"]
    assert by_id[students[0]["id"]]["score"] >= 8.0

    # persistencia: releer
    reread = client.get(f"/api/gradebook/exams/{exam['id']}/grades").json()
    assert reread["stats"]["count"] == 3
    assert all(g["graded"] for g in reread["grades"])


def test_grade_class_es_idempotente_upsert(client):
    """Reenviar corrige de nuevo sin duplicar (upsert por alumno+examen)."""
    c = _make_class(client)
    students = _add_students(client, c["id"], ["Ana"])
    exam = _make_exam(client, c["id"])
    payload = {"answers": [{"student_id": students[0]["id"], "text": "produce energía ATP"}]}
    client.post(f"/api/gradebook/exams/{exam['id']}/grade_class", json=payload)
    client.post(f"/api/gradebook/exams/{exam['id']}/grade_class", json=payload)
    grades = client.get(f"/api/gradebook/exams/{exam['id']}/grades").json()
    assert grades["stats"]["count"] == 1  # no se duplica


def test_grade_class_ignora_alumnos_de_otra_clase(client):
    c1 = _make_class(client, "Clase A")
    c2 = _make_class(client, "Clase B")
    s2 = _add_students(client, c2["id"], ["Intruso"])[0]
    exam = _make_exam(client, c1["id"])
    res = client.post(f"/api/gradebook/exams/{exam['id']}/grade_class", json={
        "answers": [{"student_id": s2["id"], "text": "produce energía ATP"}],
    })
    # el alumno no es de esta clase → ninguna respuesta válida
    assert res.status_code == 400


def test_grade_class_sin_respuestas_da_400(client):
    c = _make_class(client)
    _add_students(client, c["id"], ["Ana"])
    exam = _make_exam(client, c["id"])
    assert client.post(f"/api/gradebook/exams/{exam['id']}/grade_class",
                       json={"answers": []}).status_code == 400


def test_grade_class_examen_inexistente_da_404(client):
    assert client.post("/api/gradebook/exams/9999/grade_class",
                       json={"answers": [{"student_id": 1, "text": "x"}]}).status_code == 404


def test_grades_incluye_pendientes(client):
    """list_grades muestra a TODOS los alumnos, corregidos o no."""
    c = _make_class(client)
    students = _add_students(client, c["id"], ["Ana", "Luis"])
    exam = _make_exam(client, c["id"])
    client.post(f"/api/gradebook/exams/{exam['id']}/grade_class", json={
        "answers": [{"student_id": students[0]["id"], "text": "produce energía ATP"}],
    })
    data = client.get(f"/api/gradebook/exams/{exam['id']}/grades").json()
    assert len(data["grades"]) == 2
    assert data["stats"]["count"] == 1
    assert data["stats"]["pending"] == 1


def test_boletin_del_alumno(client):
    """grades_for_student devuelve el historial del alumno en varios exámenes."""
    c = _make_class(client)
    ana = _add_students(client, c["id"], ["Ana"])[0]
    e1 = _make_exam(client, c["id"], "Examen 1")
    e2 = _make_exam(client, c["id"], "Examen 2")
    for e in (e1, e2):
        client.post(f"/api/gradebook/exams/{e['id']}/grade_class", json={
            "answers": [{"student_id": ana["id"], "text": "produce energía ATP"}],
        })
    boletin = client.get(f"/api/gradebook/students/{ana['id']}/grades").json()
    assert len(boletin) == 2
    titles = {g["title"] for g in boletin}
    assert titles == {"Examen 1", "Examen 2"}


# ── Corregir clase por MODO (numeric / writing) ──────────────────────────────

def test_grade_class_modo_numeric_mates(client):
    """Examen de Mates: corrige por resultado, no por conceptos."""
    c = _make_class(client, "1 Bach Ciencias")
    students = _add_students(client, c["id"], ["Ana", "Luis"])
    exam = client.post(f"/api/gradebook/classes/{c['id']}/exams", json={
        "title": "Ecuaciones", "exam_date": "2026-05-21", "subject": "Matemáticas",
        "grading_mode": "numeric",
        "rubric": {"question": "Resuelve 2x+6=0", "expected": "x = -3", "kind": "math"},
    }).json()
    assert exam["rubric"]["grading_mode"] == "numeric"

    res = client.post(f"/api/gradebook/exams/{exam['id']}/grade_class", json={"answers": [
        {"student_id": students[0]["id"], "text": "2x=-6 así que x=-3"},
        {"student_id": students[1]["id"], "text": "x=-3... no, x=3"},
    ]}).json()
    by_id = {g["student_id"]: g for g in res["grades"] if g["graded"]}
    assert by_id[students[0]["id"]]["score"] == 10.0   # correcto
    assert by_id[students[1]["id"]]["score"] == 0.0    # conclusión errónea


def test_grade_class_modo_numeric_sin_expected_da_400(client):
    c = _make_class(client)
    resp = client.post(f"/api/gradebook/classes/{c['id']}/exams", json={
        "title": "X", "grading_mode": "numeric", "rubric": {"question": "?", "kind": "math"},
    })
    assert resp.status_code == 400


def test_grade_class_modo_writing_ingles(client, fake_claude):
    """Examen de Inglés: corrige con el juez LLM (mockeado)."""
    import json as _json
    fake_claude.set_text(_json.dumps({
        "criteria": [{"id": "task", "score": 2.0, "max": 2.5},
                     {"id": "grammar", "score": 2.0, "max": 2.5},
                     {"id": "vocabulary", "score": 2.0, "max": 2.5},
                     {"id": "coherence", "score": 2.0, "max": 2.5}],
        "feedback": "Good text.",
    }))
    c = _make_class(client, "1 Bach Inglés")
    students = _add_students(client, c["id"], ["Ana"])
    exam = client.post(f"/api/gradebook/classes/{c['id']}/exams", json={
        "title": "Writing Unit 5", "subject": "Inglés", "grading_mode": "writing",
        "rubric": {"question": "Write about your holidays", "subject": "ingles"},
    }).json()
    res = client.post(f"/api/gradebook/exams/{exam['id']}/grade_class", json={"answers": [
        {"student_id": students[0]["id"], "text": "Last summer I went to Italy..."},
    ]}).json()
    assert res["graded_count"] == 1
    by_id = {g["student_id"]: g for g in res["grades"] if g["graded"]}
    assert by_id[students[0]["id"]]["score"] == 8.0  # 8/10


def test_create_exam_modo_invalido_da_400(client):
    c = _make_class(client)
    resp = client.post(f"/api/gradebook/classes/{c['id']}/exams", json={
        "title": "X", "grading_mode": "telepatia", "rubric": {"question": "?"},
    })
    assert resp.status_code == 400


# ── Página /aula ──────────────────────────────────────────────────────────────

def test_aula_sirve_html(client):
    resp = client.get("/aula")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]

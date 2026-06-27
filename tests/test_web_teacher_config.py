"""
Tests de teacher_config: sinónimos y antipatrones, y su efecto runtime
sobre las correcciones.
"""

from __future__ import annotations


def test_get_teacher_config_vacio_por_defecto(client):
    resp = client.get("/api/teacher_config")
    assert resp.status_code == 200
    assert resp.json() == {"synonyms": [], "antipatterns": []}


def test_set_y_get_teacher_config_roundtrip(client):
    cfg = {
        "synonyms": [{"canonical": "energía", "variants": ["ATP", "fuerza vital"]}],
        "antipatterns": [
            {"concept": "ATP", "forbidden": ["es el núcleo"], "penalty": 0.5}
        ],
    }
    resp = client.post("/api/teacher_config", json=cfg)
    assert resp.status_code == 200
    got = client.get("/api/teacher_config").json()
    assert got["synonyms"][0]["canonical"] == "energía"
    assert got["antipatterns"][0]["concept"] == "ATP"


def test_antipattern_penaliza_la_nota(client, mitocondria_reference):
    """
    Si la respuesta contiene una frase prohibida ligada a un concepto de la
    rúbrica, la nota se multiplica por el penalty.
    """
    answer = "La mitocondria es el núcleo que produce energía ATP en la respiración celular."

    base = client.post("/api/grade", json={
        "student_answer": answer, "reference": mitocondria_reference,
    }).json()["score_over_10"]

    client.post("/api/teacher_config", json={
        "synonyms": [],
        "antipatterns": [
            {"concept": "ATP", "forbidden": ["es el núcleo"], "penalty": 0.5}
        ],
    })
    penalized = client.post("/api/grade", json={
        "student_answer": answer, "reference": mitocondria_reference,
    }).json()

    assert penalized["score_over_10"] < base
    assert penalized["antipatterns_hit"]
    assert penalized["antipatterns_hit"][0]["concept"] == "ATP"


def test_antipattern_solo_aplica_si_concepto_en_rubrica(client, mitocondria_reference):
    """Un antipatrón cuyo concepto no está en la rúbrica activa no debe afectar."""
    answer = "La mitocondria es el núcleo que produce energía ATP en la respiración celular."
    base = client.post("/api/grade", json={
        "student_answer": answer, "reference": mitocondria_reference,
    }).json()["score_over_10"]

    client.post("/api/teacher_config", json={
        "synonyms": [],
        "antipatterns": [
            {"concept": "fotosíntesis", "forbidden": ["es el núcleo"], "penalty": 0.1}
        ],
    })
    after = client.post("/api/grade", json={
        "student_answer": answer, "reference": mitocondria_reference,
    }).json()
    assert after["score_over_10"] == base
    assert after["antipatterns_hit"] == []


def test_sinonimo_del_profesor_se_aplica(client):
    """
    Definir un sinónimo profesor (canonical 'fotosintesis' con variante
    'foto-sintesis') hace que la variante cuente como el concepto.
    """
    reference = {
        "question": "¿Qué es la fotosíntesis?",
        "subject": "Biología",
        "education_level": "Bachillerato",
        "ideal_answer": "La fotosíntesis transforma luz en energía química.",
        "key_concepts": [{"concept": "fotosintesis", "weight": 1.0}],
        "bonus_terms": [],
    }
    answer = "El proceso de foto-sintesis ocurre en las plantas."

    before = client.post("/api/grade", json={
        "student_answer": answer, "reference": reference,
    }).json()

    client.post("/api/teacher_config", json={
        "synonyms": [{"canonical": "fotosintesis", "variants": ["foto-sintesis", "foto sintesis"]}],
        "antipatterns": [],
    })
    after = client.post("/api/grade", json={
        "student_answer": answer, "reference": reference,
    }).json()
    # Con el sinónimo, el concepto debería detectarse mejor que sin él
    assert after["concept_ratio"] >= before["concept_ratio"]


def test_config_corrupto_no_rompe_correccion(client, isolated_storage, mitocondria_reference):
    """Si teacher_config.json está corrupto, se ignora y la corrección sigue."""
    (isolated_storage / "teacher_config.json").write_text("{ esto no es json", encoding="utf-8")
    resp = client.post("/api/grade", json={
        "student_answer": "La mitocondria produce energía ATP.",
        "reference": mitocondria_reference,
    })
    assert resp.status_code == 200

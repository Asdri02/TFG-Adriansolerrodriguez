"""
Tests de CORRECCIÓN (no solo de "responde 200"): verifican que el sistema
califica BIEN, no solo que califica.

Estrategia:
  - Oráculos calculados a mano sobre referencias sintéticas (conceptos que NO
    están en el synonym_map del grader, para aislar la lógica de pesos).
  - Invariantes que deben cumplirse SIEMPRE (cotas, determinismo).
  - Propiedades (monotonía: mejor respuesta ⇒ nota ≥).
  - Consistencia con la fórmula publicada del grader.
  - Exactitud aritmética de estadísticas y de la corrección celda a celda,
    recomputada de forma independiente con la stdlib.
"""

from __future__ import annotations

import statistics

import pytest


# ── Referencias sintéticas controladas ───────────────────────────────────────
#
# Usamos palabras inventadas (alfa, beta, gamma, delta) que no aparecen en el
# synonym_map de SemanticGrader, así el concept_ratio es 100% predecible.

def _ref(concepts, ideal=None, bonus=None):
    ideal = ideal or " ".join(c["concept"] for c in concepts)
    return {
        "question": "pregunta sintética",
        "subject": "Test",
        "education_level": "Test",
        "ideal_answer": ideal,
        "key_concepts": concepts,
        "bonus_terms": bonus or [],
    }


FOUR_EQUAL = [
    {"concept": "alfa", "weight": 0.25},
    {"concept": "beta", "weight": 0.25},
    {"concept": "gamma", "weight": 0.25},
    {"concept": "delta", "weight": 0.25},
]


def _grade(client, answer, reference):
    r = client.post("/api/grade", json={"student_answer": answer, "reference": reference})
    assert r.status_code == 200
    return r.json()


def _expected_score(concept_ratio, similarity, length_penalty, bonus_weights):
    """Reimplementación independiente de la fórmula publicada del grader."""
    final = (0.95 * concept_ratio + 0.05 * similarity) * length_penalty
    floor = 0.6 if concept_ratio >= 0.6 else 0.0
    final = max(final, floor)
    final = max(0.0, min(final, 1.0))
    if bonus_weights:
        final = min(final + sum(bonus_weights), 1.0)
    return round(final * 10, 2)


# ── 1. Oráculos exactos ──────────────────────────────────────────────────────

def test_respuesta_perfecta_saca_10(client):
    ref = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta")
    out = _grade(client, "alfa beta gamma delta", ref)
    assert out["concept_ratio"] == 1.0
    assert out["similarity_ratio"] == 1.0
    assert out["length_penalty"] == 1.0
    assert out["score_over_10"] == 10.0
    assert sorted(out["detected_concepts"]) == ["alfa", "beta", "delta", "gamma"]
    assert out["missing_concepts"] == []


def test_concept_ratio_pesos_exactos(client):
    """Pesos desiguales: el ratio debe ser la suma de pesos detectados / total."""
    ref = _ref([
        {"concept": "alfa", "weight": 0.5},
        {"concept": "beta", "weight": 0.3},
        {"concept": "gamma", "weight": 0.2},
    ], ideal="alfa beta gamma blah blah blah blah blah")
    # Solo 'alfa' y 'gamma' presentes → ratio = (0.5+0.2)/1.0 = 0.7
    out = _grade(client, "alfa gamma respuesta larga de relleno aqui va texto", ref)
    assert out["concept_ratio"] == 0.7
    assert "beta" in out["missing_concepts"]


def test_respuesta_vacia_saca_0(client):
    ref = _ref(FOUR_EQUAL)
    out = _grade(client, "", ref)
    assert out["score_over_10"] == 0.0
    assert out["concept_ratio"] == 0.0
    assert sorted(out["missing_concepts"]) == ["alfa", "beta", "delta", "gamma"]


def test_respuesta_irrelevante_saca_bajo(client):
    ref = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta")
    out = _grade(client, "esto no tiene nada que ver con el tema preguntado", ref)
    assert out["concept_ratio"] == 0.0
    assert out["score_over_10"] <= 1.0


# ── 2. Invariantes (deben cumplirse SIEMPRE) ─────────────────────────────────

@pytest.mark.parametrize("answer", [
    "", "alfa", "alfa beta", "alfa beta gamma", "alfa beta gamma delta",
    "alfa alfa alfa", "texto irrelevante", "delta gamma beta alfa extra extra",
])
def test_invariante_score_en_rango(client, answer):
    ref = _ref(FOUR_EQUAL)
    out = _grade(client, answer, ref)
    assert 0.0 <= out["score_over_10"] <= 10.0
    assert 0.0 <= out["concept_ratio"] <= 1.0
    assert 0.0 <= out["similarity_ratio"] <= 1.0
    assert 0.7 <= out["length_penalty"] <= 1.0


def test_invariante_score_en_los_35_casos(client):
    """Ningún caso de la suite puede producir una nota fuera de [0,10]."""
    cases = client.get("/api/cases").json()
    for c in cases:
        out = client.post("/api/grade_case", json={"case_id": c["id"]}).json()
        assert 0.0 <= out["score_over_10"] <= 10.0, f"caso {c['id']} fuera de rango"


def test_determinismo(client):
    """Misma entrada ⇒ misma nota (sin aleatoriedad)."""
    ref = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta")
    a = _grade(client, "alfa beta gamma", ref)["score_over_10"]
    b = _grade(client, "alfa beta gamma", ref)["score_over_10"]
    assert a == b


# ── 3. Propiedades: monotonía (mejor respuesta ⇒ nota no menor) ───────────────

def test_monotonia_anadir_concepto_no_baja_nota(client):
    ref = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta")
    # Respuestas de longitud suficiente para que length_penalty no enturbie
    parcial = _grade(client, "alfa beta gamma relleno", ref)
    completa = _grade(client, "alfa beta gamma delta", ref)
    assert completa["concept_ratio"] > parcial["concept_ratio"]
    assert completa["score_over_10"] >= parcial["score_over_10"]


def test_ranking_coherente_peor_a_mejor(client):
    """El orden de notas debe respetar el orden de calidad real."""
    ref = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta")
    nula = _grade(client, "nada relevante aqui", ref)["score_over_10"]
    una = _grade(client, "alfa relleno relleno relleno", ref)["score_over_10"]
    tres = _grade(client, "alfa beta gamma relleno", ref)["score_over_10"]
    todas = _grade(client, "alfa beta gamma delta", ref)["score_over_10"]
    assert nula <= una <= tres <= todas


# ── 4. Consistencia con la fórmula publicada ─────────────────────────────────

@pytest.mark.parametrize("answer", [
    "alfa", "alfa beta", "alfa beta gamma", "alfa beta gamma delta",
    "alfa beta gamma delta extra extra extra", "beta delta",
])
def test_score_coincide_con_formula_documentada(client, answer):
    """
    Recomputa la nota a partir de los componentes que devuelve el endpoint y la
    compara con la nota publicada. Verifica que el grader aplica su propia regla
    de forma coherente (tolerancia por el redondeo de los ratios a 3 decimales).
    """
    ref = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta")
    out = _grade(client, answer, ref)
    expected = _expected_score(
        out["concept_ratio"], out["similarity_ratio"],
        out["length_penalty"], [b["weight"] for b in out["bonus_hits"]],
    )
    assert abs(out["score_over_10"] - expected) <= 0.05, (
        f"answer={answer!r}: publicada={out['score_over_10']} vs fórmula={expected}"
    )


def test_min_floor_evita_suspenso_por_brevedad(client):
    """
    Regla de suelo: si concept_ratio ≥ 0.6, la nota no debe bajar de 6.0 aunque
    la respuesta sea muy corta (length_penalty agresivo).
    """
    ref = _ref([
        {"concept": "alfa", "weight": 0.3},
        {"concept": "beta", "weight": 0.3},
        {"concept": "gamma", "weight": 0.2},
        {"concept": "delta", "weight": 0.2},
    ], ideal="alfa beta gamma delta texto largo de referencia para forzar el ratio de longitud bajo")
    out = _grade(client, "alfa beta", ref)  # ratio = 0.6 exacto, respuesta muy corta
    assert out["concept_ratio"] >= 0.6
    assert out["score_over_10"] >= 6.0


# ── 5. Bonus: aditivo pero acotado (no puede romper la escala) ───────────────

def test_bonus_nunca_supera_10(client):
    ref = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta",
               bonus=[{"term": "alfa", "weight": 5.0}])  # peso absurdo a propósito
    out = _grade(client, "alfa beta gamma delta", ref)
    assert out["score_over_10"] == 10.0  # capado, no 60


def test_bonus_sube_pero_se_aplica_solo_si_presente(client):
    ref_sin = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta")
    ref_con = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta",
                   bonus=[{"term": "tecnicismo", "weight": 0.2}])
    base = _grade(client, "alfa beta relleno relleno", ref_sin)["score_over_10"]
    # el término bonus NO está en la respuesta ⇒ no debe cambiar nada
    sin_hit = _grade(client, "alfa beta relleno relleno", ref_con)
    assert sin_hit["bonus_hits"] == []
    assert sin_hit["score_over_10"] == base
    # ahora SÍ está ⇒ sube
    con_hit = _grade(client, "alfa beta tecnicismo relleno", ref_con)
    assert con_hit["bonus_hits"]
    assert con_hit["score_over_10"] >= base


# ── 6. Antipatrón: multiplica exactamente por el penalty ─────────────────────

def test_antipatron_multiplica_exacto(client):
    ref = _ref([{"concept": "alfa", "weight": 1.0}], ideal="alfa es lo correcto y verdadero")
    answer = "alfa es falso y ademas alfa es un error grave"
    base = _grade(client, answer, ref)["score_over_10"]

    client.post("/api/teacher_config", json={
        "synonyms": [],
        "antipatterns": [{"concept": "alfa", "forbidden": ["alfa es falso"], "penalty": 0.5}],
    })
    after = _grade(client, answer, ref)
    assert after["antipatterns_hit"]
    assert after["score_over_10"] == round(base * 0.5, 2)


def test_antipatron_es_insensible_a_tildes(client):
    """
    Regresión del bug arreglado: _apply_antipatterns normaliza ambos lados, así
    que un antipatrón escrito 'es el nucleo' salta también contra 'es el núcleo'.
    """
    ref = _ref([{"concept": "nucleo", "weight": 1.0}],
               ideal="el nucleo guarda el material genetico de la celula")
    answer = "la mitocondria es el núcleo de la célula"
    base = _grade(client, answer, ref)["score_over_10"]

    client.post("/api/teacher_config", json={
        "synonyms": [],
        # el profesor escribe la regla SIN tildes (lo natural)
        "antipatterns": [{"concept": "nucleo", "forbidden": ["es el nucleo"], "penalty": 0.5}],
    })
    after = _grade(client, answer, ref)
    # Comportamiento CORRECTO esperado: debería penalizar igualmente.
    assert after["antipatterns_hit"], "el antipatrón debería saltar pese a la tilde"
    assert after["score_over_10"] == round(base * 0.5, 2)


# ── 7. Estadísticas de lote: aritmética exacta ───────────────────────────────

def test_batch_stats_recomputadas(client):
    ref = _ref(FOUR_EQUAL, ideal="alfa beta gamma delta")
    answers = [
        {"text": "alfa beta gamma delta"},
        {"text": "alfa beta gamma relleno"},
        {"text": "alfa relleno relleno relleno"},
        {"text": "nada que ver con esto"},
    ]
    data = client.post("/api/grade_batch", json={"reference": ref, "answers": answers}).json()
    scores = [r["score"] for r in data["results"]]
    s = data["stats"]
    assert s["count"] == len(scores)
    assert s["mean"] == round(statistics.mean(scores), 2)
    assert s["median"] == round(statistics.median(scores), 2)
    assert s["stdev"] == round(statistics.stdev(scores), 2)
    assert s["min"] == round(min(scores), 2)
    assert s["max"] == round(max(scores), 2)
    assert s["pass_count"] == sum(1 for x in scores if x >= 5)
    assert s["fail_count"] == sum(1 for x in scores if x < 5)
    assert s["pass_count"] + s["fail_count"] == len(scores)
    # el histograma debe contabilizar exactamente todas las notas
    assert sum(data["histogram"]["values"]) == len(scores)


# ── 8. Corrección estructurada: aritmética de puntos exacta ──────────────────

def test_estructurada_puntos_exactos(client):
    """earned = Σ puntos por celda; parcial = 0.7·ppc; score_over_10 = pct/10."""
    structure = {
        "type": "table",
        "rows": [
            [{"kind": "printed", "text": "Q1"}, {"kind": "student", "text": "agua"}],          # correcto
            [{"kind": "printed", "text": "Q2"}, {"kind": "student", "text": "dioxido de carbon"}],  # parcial
            [{"kind": "printed", "text": "Q3"}, {"kind": "student", "text": "plutonio"}],       # wrong
            [{"kind": "printed", "text": "Q4"}, {"kind": "blank", "text": ""}],                  # blank
        ],
    }
    solutions = [
        {"row": 0, "col": 1, "correct": "agua"},
        {"row": 1, "col": 1, "correct": "dioxido de carbono"},
        {"row": 2, "col": 1, "correct": "oxigeno"},
        {"row": 3, "col": 1, "correct": "sal"},
    ]
    data = client.post("/api/grade_structured", json={
        "structure": structure, "solutions": solutions,
        "fuzzy_threshold": 0.8, "points_per_cell": 2.0,
    }).json()

    by_row = {c["row"]: c for c in data["cells"]}
    assert by_row[0]["verdict"] == "correct" and by_row[0]["points"] == 2.0
    assert by_row[1]["verdict"] == "partial" and by_row[1]["points"] == round(2.0 * 0.7, 2)
    assert by_row[2]["verdict"] == "wrong" and by_row[2]["points"] == 0.0
    assert by_row[3]["verdict"] == "blank" and by_row[3]["points"] == 0.0

    assert data["max_points"] == 8.0
    assert data["earned"] == round(sum(c["points"] for c in data["cells"]), 2)
    assert data["earned"] == round(2.0 + 1.4, 2)
    assert data["score_pct"] == round(data["earned"] / data["max_points"] * 100, 1)
    assert data["score_over_10"] == round(data["score_pct"] / 10, 2)

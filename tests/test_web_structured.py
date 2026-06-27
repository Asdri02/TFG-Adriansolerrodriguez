"""
Tests de la corrección estructurada celda a celda:
  - helpers puros (_normalize_for_compare, _apply_synonyms, _grade_cells,
    _structure_to_solutions)
  - endpoint /api/grade_structured
"""

from __future__ import annotations

import pytest

from web import app as app_module


# ── Helpers puros ────────────────────────────────────────────────────────────

def test_normalize_for_compare_quita_acentos_y_puntuacion():
    n = app_module._normalize_for_compare
    assert n("  Dióxido, de Carbono!! ") == "dioxido de carbono"
    # OJO: aunque el regex incluye 'ñ' para preservarla, la normalización NFD +
    # descarte de combining marks ocurre ANTES y descompone ñ→n+tilde, borrando
    # la tilde. Resultado: ñ→n y la 'ñ' del regex es código muerto. (Hallazgo)
    assert n("ñandú") == "nandu"
    assert n("") == ""
    assert n(None) == ""


def test_apply_synonyms_reemplaza_variantes_por_canonico():
    synonyms = [{"canonical": "agua", "variants": ["h2o", "monóxido de dihidrógeno"]}]
    out = app_module._apply_synonyms(
        app_module._normalize_for_compare("h2o"), synonyms
    )
    assert "agua" in out


def test_structure_to_solutions_solo_evaluables_con_correct():
    structure = {
        "rows": [
            [
                {"role": "context", "text": "H2O"},
                {"role": "evaluable", "correct": "agua"},
                {"role": "evaluable", "correct": ""},     # sin correct → se ignora
                {"role": "none"},
            ],
        ],
    }
    sols = app_module._structure_to_solutions(structure)
    assert sols == [{"row": 0, "col": 1, "correct": "agua"}]


# ── _grade_cells ─────────────────────────────────────────────────────────────

def _structure_rows(student_texts):
    """Construye filas con una celda printed y una student por par."""
    rows = []
    for printed, student, kind in student_texts:
        rows.append([
            {"kind": "printed", "text": printed},
            {"kind": kind, "text": student},
        ])
    return rows


def test_grade_cells_correcto_parcial_blank_wrong(client):
    rows = _structure_rows([
        ("H2O", "agua", "student"),                 # correcto
        ("CO2", "dioxido de carbon", "student"),    # parcial (fuzzy)
        ("NaCl", "", "blank"),                       # en blanco
        ("O2", "plutonio", "student"),               # incorrecto
    ])
    solutions = [
        {"row": 0, "col": 1, "correct": "agua"},
        {"row": 1, "col": 1, "correct": "dioxido de carbono"},
        {"row": 2, "col": 1, "correct": "cloruro de sodio"},
        {"row": 3, "col": 1, "correct": "oxigeno"},
    ]
    result = app_module._grade_cells(rows, solutions, fuzzy_threshold=0.80, points_per_cell=1.0)
    verdicts = {c["row"]: c["verdict"] for c in result["cells"]}
    assert verdicts[0] == "correct"
    assert verdicts[1] == "partial"
    assert verdicts[2] == "blank"
    assert verdicts[3] == "wrong"
    assert result["max_points"] == 4.0
    assert result["earned"] == pytest.approx(1.0 + 0.7)  # correcto + parcial(0.7)
    assert result["score_over_10"] == round(result["score_pct"] / 10, 2)


def test_grade_cells_ignora_indices_fuera_de_rango(client):
    rows = _structure_rows([("H2O", "agua", "student")])
    solutions = [
        {"row": 0, "col": 1, "correct": "agua"},
        {"row": 5, "col": 0, "correct": "x"},   # fila inexistente → ignorada
        {"row": 0, "col": 9, "correct": "y"},   # col inexistente → ignorada
    ]
    result = app_module._grade_cells(rows, solutions)
    assert result["max_points"] == 1.0
    assert len(result["cells"]) == 1


def test_grade_cells_guiones_cuentan_como_blank(client):
    rows = _structure_rows([("H2O", "---", "student")])
    solutions = [{"row": 0, "col": 1, "correct": "agua"}]
    result = app_module._grade_cells(rows, solutions)
    assert result["cells"][0]["verdict"] == "blank"


def test_grade_cells_sin_soluciones_no_divide_por_cero(client):
    result = app_module._grade_cells([], [])
    assert result["max_points"] == 0.0
    assert result["score_pct"] == 0.0
    assert result["score_over_10"] == 0.0


# ── Endpoint /api/grade_structured ───────────────────────────────────────────

def test_grade_structured_endpoint(client):
    resp = client.post("/api/grade_structured", json={
        "structure": {
            "type": "table",
            "rows": [
                [{"kind": "printed", "text": "H2O"}, {"kind": "student", "text": "agua"}],
            ],
        },
        "solutions": [{"row": 0, "col": 1, "correct": "agua"}],
        "fuzzy_threshold": 0.8,
        "points_per_cell": 1.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["score_over_10"] == 10.0
    assert data["cells"][0]["verdict"] == "correct"

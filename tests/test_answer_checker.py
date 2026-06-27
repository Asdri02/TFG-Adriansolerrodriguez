"""
Tests del checker determinista numérico/simbólico (Mates y Física).
Pura lógica, sin web ni LLM.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai import answer_checker as ac


# ── Matemáticas: equivalencia, no coincidencia textual ───────────────────────

@pytest.mark.parametrize("student", [
    "Despejo 2x = -6 y queda x = -3",
    "x = -3",
    "x=-6/2",
    "el resultado es -3",
    "x = -3.0",
])
def test_math_resultados_equivalentes_son_correctos(student):
    r = ac.grade_numeric(student, "x = -3", kind="math")
    assert r["correct"] is True
    assert r["score_over_10"] == 10.0


def test_math_conclusion_erronea_aunque_aparezca_la_clave():
    """El fallo que tenía el grader: '...x=-3... no, x=3' debe ser INCORRECTO."""
    r = ac.grade_numeric("Primero pongo 2x=-6, x=-3... no, en realidad x = 3", "x = -3", kind="math")
    assert r["correct"] is False
    assert r["score_over_10"] == 0.0


def test_math_incorrecto():
    r = ac.grade_numeric("x = 7", "x = -3", kind="math")
    assert r["correct"] is False
    assert r["score_over_10"] == 0.0


def test_math_varias_soluciones():
    r = ac.grade_numeric("las soluciones son x = 2 y x = -2", "2, -2", kind="math")
    assert r["correct"] is True


def test_math_fraccion_equivale_a_decimal():
    r = ac.grade_numeric("x = 0.5", "1/2", kind="math")
    assert r["correct"] is True


def test_math_en_blanco():
    r = ac.grade_numeric("   ", "x = -3", kind="math")
    assert r["score_over_10"] == 0.0
    assert r["correct"] is False


# ── Física: valor + unidad ───────────────────────────────────────────────────

def test_physics_valor_y_unidad_correctos():
    r = ac.grade_numeric("La aceleración es 9.8 m/s^2", "9.8 m/s^2", kind="physics")
    assert r["correct"] is True
    assert r["score_over_10"] == 10.0


def test_physics_tolerancia_relativa():
    """9.81 frente a 9.8 esperado entra dentro del 5% de tolerancia."""
    r = ac.grade_numeric("a = 9.81 m/s^2", "9.8 m/s^2", kind="physics")
    assert r["correct"] is True


def test_physics_valor_ok_unidad_mal_credito_parcial():
    r = ac.grade_numeric("9.8 m/s", "9.8 m/s^2", kind="physics")
    assert r["correct"] is False
    assert r["value_ok"] is True
    assert r["unit_ok"] is False
    assert r["score_over_10"] == 6.0


def test_physics_valor_incorrecto():
    r = ac.grade_numeric("a = 3 m/s^2", "9.8 m/s^2", kind="physics")
    assert r["correct"] is False
    assert r["score_over_10"] == 0.0


def test_physics_unidad_equivalente_normalizada():
    r = ac.grade_numeric("v = 20 metros/segundo", "20 m/s", kind="physics")
    assert r["correct"] is True


def test_physics_no_confunde_constante_del_procedimiento_con_resultado():
    """Cita g=9.8 al operar pero concluye a=3 m/s^2 → debe ser INCORRECTO."""
    r = ac.grade_numeric("uso g=9.8 pero me da a = 3 m/s^2", "9.8 m/s^2", kind="physics")
    assert r["correct"] is False
    assert r["score_over_10"] == 0.0


def test_physics_autocorreccion_gana_el_resultado_final():
    """Escribe un valor mal y luego lo corrige al bueno → CORRECTO."""
    r = ac.grade_numeric("a = 3 m/s^2... me equivoqué, a = 9.8 m/s^2", "9.8 m/s^2", kind="physics")
    assert r["correct"] is True

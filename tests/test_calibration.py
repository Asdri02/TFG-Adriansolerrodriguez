"""
Tests de la capa de calibración determinista (lineal e isotónica).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai import metrics
from ai.calibration import ScoreCalibrator


def test_linear_recupera_relacion_afin():
    # teacher = 2*raw + 1 (exacto) → la lineal debe recuperarlo
    raw = [0, 1, 2, 3, 4]
    teacher = [1, 3, 5, 7, 9]
    cal = ScoreCalibrator("linear").fit(raw, teacher)
    assert cal.transform(2) == pytest.approx(5.0, abs=0.01)
    assert cal.transform(4) == pytest.approx(9.0, abs=0.01)


def test_linear_corrige_sesgo_constante():
    # teacher = raw + 4 (sistema severo) → calibración suma ~4
    raw = [1, 2, 3, 4, 5]
    teacher = [5, 6, 7, 8, 9]
    cal = ScoreCalibrator("linear").fit(raw, teacher)
    assert cal.transform(3) == pytest.approx(7.0, abs=0.01)


def test_transform_clipa_a_0_10():
    cal = ScoreCalibrator("linear").fit([0, 10], [5, 50])  # pendiente enorme
    assert cal.transform(10) <= 10.0
    assert cal.transform(0) >= 0.0


def test_isotonic_es_monotono_y_preserva_orden():
    raw = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    teacher = [1, 0, 3, 2, 5, 6, 5, 8, 9, 8, 10]  # ruidoso pero creciente
    cal = ScoreCalibrator("isotonic").fit(raw, teacher)
    out = cal.transform_many(raw)
    # monótono no decreciente
    assert all(out[i] <= out[i + 1] + 1e-9 for i in range(len(out) - 1))


def test_isotonic_no_cambia_spearman():
    # un mapeo monótono no altera el orden → Spearman idéntico
    raw = [2.0, 1.0, 5.0, 4.0, 3.0, 8.0, 7.0]
    teacher = [4.0, 3.0, 9.0, 7.0, 6.0, 10.0, 9.5]
    cal = ScoreCalibrator("isotonic").fit(raw, teacher)
    cal_scores = cal.transform_many(raw)
    assert metrics.spearman(raw, teacher) == pytest.approx(
        metrics.spearman(cal_scores, teacher), abs=1e-9
    )


def test_pocos_datos_falla():
    with pytest.raises(ValueError):
        ScoreCalibrator("linear").fit([1.0], [2.0])

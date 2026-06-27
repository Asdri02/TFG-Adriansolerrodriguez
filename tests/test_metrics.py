"""
Tests de las métricas de concordancia (Spearman, Pearson, MAE, RMSE).
Valores comprobables a mano; sin scipy.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai import metrics


def test_spearman_perfecto():
    assert metrics.spearman([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)


def test_spearman_inverso():
    assert metrics.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_spearman_un_intercambio():
    # x=[1,2,3,4], y=[1,2,4,3] -> sum d^2 = 2 -> rho = 1 - 6*2/(4*15) = 0.8
    assert metrics.spearman([1, 2, 3, 4], [1, 2, 4, 3]) == pytest.approx(0.8)


def test_spearman_con_empates():
    # ranks y = [1.5,1.5,3.5,3.5] -> pearson de rangos = 4/sqrt(20)
    val = metrics.spearman([1, 2, 3, 4], [1, 1, 2, 2])
    assert val == pytest.approx(4 / math.sqrt(20))


def test_pearson_basico():
    assert metrics.pearson([1, 2, 3, 4], [1, 2, 4, 3]) == pytest.approx(0.8)


def test_pearson_sin_varianza_es_cero():
    assert metrics.pearson([5, 5, 5], [1, 2, 3]) == 0.0


def test_mae_y_rmse():
    assert metrics.mae([1, 2, 3, 4], [1, 2, 4, 3]) == pytest.approx(0.5)
    assert metrics.rmse([1, 2, 3, 4], [1, 2, 4, 3]) == pytest.approx(math.sqrt(0.5))


def test_average_ranks_empata_promediando():
    assert metrics._average_ranks([10, 8, 8, 5]) == [4.0, 2.5, 2.5, 1.0]


def test_report_estructura():
    rep = metrics.correlation_report([1, 2, 3, 4, 5], [1.5, 2.0, 3.1, 3.9, 5.2])
    assert rep["n"] == 5
    assert 0.9 <= rep["spearman"] <= 1.0
    assert rep["mae"] >= 0.0


def test_longitudes_distintas_falla():
    with pytest.raises(ValueError):
        metrics.pearson([1, 2, 3], [1, 2])


def test_bootstrap_ci_envuelve_correlacion_alta():
    x = list(range(20))
    y = [v + (1 if v % 2 else -1) * 0.3 for v in x]  # casi perfecto
    lo, hi = metrics.bootstrap_ci(x, y, stat=metrics.spearman, n=500, seed=1)
    assert lo <= metrics.spearman(x, y) <= hi
    assert hi <= 1.0 and lo >= 0.0


def test_bootstrap_ci_pocos_datos_es_nan():
    lo, hi = metrics.bootstrap_ci([1, 2], [1, 2])
    assert lo != lo and hi != hi  # NaN

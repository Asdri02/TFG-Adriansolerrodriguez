"""
metrics.py — Métricas de concordancia entre la nota del sistema y la del profesor.

Sin dependencias pesadas (no usa scipy): implementación directa e interpretable,
coherente con el resto del proyecto. La métrica principal es la correlación de
Spearman (rho), que mide si el sistema ORDENA las respuestas igual que un humano
—lo que de verdad importa en corrección—, robusta a que la escala no sea idéntica.

Se acompañan de Pearson (r), el error absoluto medio (MAE) y la raíz del error
cuadrático medio (RMSE) para cuantificar también la distancia en la escala 0-10.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence


def _average_ranks(values: Sequence[float]) -> List[float]:
    """
    Rangos 1..n con EMPATES promediados (método estándar para Spearman).
    Ej.: [10, 8, 8, 5] -> [1.0, 2.5, 2.5, 4.0].
    """
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        # posiciones i..j son empate -> rango promedio (1-indexado)
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    """Coeficiente de correlación de Pearson. Devuelve 0.0 si no hay varianza."""
    if len(x) != len(y):
        raise ValueError("x e y deben tener la misma longitud")
    n = len(x)
    if n < 2:
        raise ValueError("se necesitan al menos 2 pares")
    mx = sum(x) / n
    my = sum(y) / n
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sxx = sum((xi - mx) ** 2 for xi in x)
    syy = sum((yi - my) ** 2 for yi in y)
    if sxx == 0 or syy == 0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Correlación de Spearman = Pearson sobre los rangos (con empates promediados)."""
    return pearson(_average_ranks(x), _average_ranks(y))


def mae(x: Sequence[float], y: Sequence[float]) -> float:
    """Error absoluto medio entre dos series (misma escala)."""
    if len(x) != len(y):
        raise ValueError("x e y deben tener la misma longitud")
    return sum(abs(a - b) for a, b in zip(x, y)) / len(x)


def rmse(x: Sequence[float], y: Sequence[float]) -> float:
    """Raíz del error cuadrático medio."""
    if len(x) != len(y):
        raise ValueError("x e y deben tener la misma longitud")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(x, y)) / len(x))


def bootstrap_ci(x: Sequence[float], y: Sequence[float], stat=spearman,
                 n: int = 2000, alpha: float = 0.05, seed: int = 0):
    """
    Intervalo de confianza de un estadístico por bootstrap de percentiles.
    Remuestrea N veces los pares (x, y) con reemplazo y devuelve (lo, hi) al
    nivel 1-alpha. Útil para dar incertidumbre a Spearman/MAE sin asumir
    normalidad. Devuelve (nan, nan) si no hay datos suficientes.
    """
    import random
    m = len(x)
    if m < 3:
        return float("nan"), float("nan")
    rnd = random.Random(seed)
    vals = []
    for _ in range(n):
        idx = [rnd.randrange(m) for _ in range(m)]
        xs = [x[i] for i in idx]
        ys = [y[i] for i in idx]
        try:
            vals.append(stat(xs, ys))
        except Exception:
            continue
    if not vals:
        return float("nan"), float("nan")
    vals.sort()
    lo = vals[int((alpha / 2) * len(vals))]
    hi = vals[min(len(vals) - 1, int((1 - alpha / 2) * len(vals)))]
    return round(lo, 4), round(hi, 4)


def correlation_report(system: Sequence[float], human: Sequence[float]) -> Dict[str, float]:
    """
    Resumen de concordancia sistema-vs-humano sobre N pares de notas (0-10).
    """
    return {
        "n": len(system),
        "spearman": round(spearman(system, human), 4),
        "pearson": round(pearson(system, human), 4),
        "mae": round(mae(system, human), 4),
        "rmse": round(rmse(system, human), 4),
    }

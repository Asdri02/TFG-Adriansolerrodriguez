"""
calibration.py — Calibración determinista de la nota del grader a la escala del
profesor.

La validación externa (Mohler) mostró que el grader ordena razonablemente pero en
una escala más SEVERA que la de los correctores humanos (media 4,2 vs 8,4): el
error es sobre todo un desfase de escala, no de criterio. Esta capa aprende, a
partir de pares (nota_grader, nota_profesor), un mapeo MONÓTONO que corrige ese
desfase sin alterar el orden de las respuestas.

Dos métodos:
  - "linear":   nota = clip(a·cruda + b, 0, 10).  Interpretable (pendiente+sesgo).
  - "isotonic": regresión isotónica (PAVA). Mapeo monótono no paramétrico; al ser
                monótono NO cambia el Spearman y minimiza el error cuadrático bajo
                esa restricción. Más robusto cuando la relación no es una recta.

Es determinista e interpretable (sin LLM): complementa a `/api/calibrate_grade`
(que usa few-shot con un LLM). Aquí basta con un puñado de notas del profesor.
"""

from __future__ import annotations

from typing import List, Sequence


def _clip(v: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, v))


def _linear_fit(x: Sequence[float], y: Sequence[float]):
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    if sxx == 0:
        return 0.0, my  # sin varianza en x: predice la media
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    a = sxy / sxx
    b = my - a * mx
    return a, b


def _isotonic_fit(x: Sequence[float], y: Sequence[float]):
    """
    Regresión isotónica creciente por PAVA (pool adjacent violators).
    Devuelve (xs, ys) crecientes que definen una función escalonada/interpolable.
    """
    order = sorted(range(len(x)), key=lambda i: x[i])
    xs = [float(x[i]) for i in order]
    ys = [float(y[i]) for i in order]

    # Bloques: (suma, peso, x_repr). Fusionamos mientras se viole la monotonía.
    vals: List[float] = []
    wts: List[float] = []
    xrep: List[float] = []
    for xi, yi in zip(xs, ys):
        vals.append(yi)
        wts.append(1.0)
        xrep.append(xi)
        while len(vals) > 1 and vals[-2] / wts[-2] > vals[-1] / wts[-1]:
            v = vals.pop() + vals[-1]
            w = wts.pop() + wts[-1]
            xr = xrep.pop()
            vals[-1] = v
            wts[-1] = w
            xrep[-1] = xr  # x del bloque = mayor x fusionado (frontera derecha)
    fitted_x = xrep
    fitted_y = [v / w for v, w in zip(vals, wts)]
    return fitted_x, fitted_y


def _isotonic_predict(fitted_x, fitted_y, q: float) -> float:
    if not fitted_x:
        return q
    if q <= fitted_x[0]:
        return fitted_y[0]
    if q >= fitted_x[-1]:
        return fitted_y[-1]
    # interpolación lineal entre los dos puntos ajustados que rodean a q
    lo = 0
    hi = len(fitted_x) - 1
    for i in range(len(fitted_x) - 1):
        if fitted_x[i] <= q <= fitted_x[i + 1]:
            lo, hi = i, i + 1
            break
    x0, x1 = fitted_x[lo], fitted_x[hi]
    y0, y1 = fitted_y[lo], fitted_y[hi]
    if x1 == x0:
        return y1
    t = (q - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)


class ScoreCalibrator:
    """
    Aprende un mapeo nota_grader → nota_profesor y lo aplica.

    Uso:
        cal = ScoreCalibrator(method="isotonic").fit(raw_scores, teacher_scores)
        nota = cal.transform(grader_score)
    """

    def __init__(self, method: str = "linear"):
        if method not in ("linear", "isotonic"):
            raise ValueError("method debe ser 'linear' o 'isotonic'")
        self.method = method
        self.fitted = False
        self.a = 1.0
        self.b = 0.0
        self._ix: List[float] = []
        self._iy: List[float] = []

    def fit(self, raw: Sequence[float], teacher: Sequence[float]) -> "ScoreCalibrator":
        if len(raw) != len(teacher):
            raise ValueError("raw y teacher deben tener la misma longitud")
        if len(raw) < 2:
            raise ValueError("se necesitan al menos 2 pares para calibrar")
        if self.method == "linear":
            self.a, self.b = _linear_fit(raw, teacher)
        else:
            self._ix, self._iy = _isotonic_fit(raw, teacher)
        self.fitted = True
        return self

    def transform(self, score: float) -> float:
        if not self.fitted:
            return score
        if self.method == "linear":
            return round(_clip(self.a * score + self.b), 2)
        return round(_clip(_isotonic_predict(self._ix, self._iy, score)), 2)

    def transform_many(self, scores: Sequence[float]) -> List[float]:
        return [self.transform(s) for s in scores]

    def describe(self) -> str:
        if not self.fitted:
            return "sin ajustar"
        if self.method == "linear":
            return f"lineal: nota = clip({self.a:.3f}·cruda + {self.b:.3f}, 0, 10)"
        return f"isotónica: {len(self._ix)} tramos monótonos"

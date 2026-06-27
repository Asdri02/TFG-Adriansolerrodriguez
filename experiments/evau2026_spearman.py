"""
Validación por CORRELACIÓN: ¿la nota del sistema concuerda con la del profesor?

La validación por bandas (validate.py) responde a "¿la nota cae donde debería?".
Esta otra responde a algo más exigente y más informativo para un tribunal:
"¿el sistema ORDENA las respuestas como un humano y se aproxima a su nota?".

Para ello tomamos el conjunto `gold_dataset.GOLD` (respuestas con nota humana de
referencia), las corregimos con el SemanticGrader y calculamos:

  - Spearman (rho): concordancia de ORDEN. Es la métrica principal: a un profesor
    le importa sobre todo que el mejor saque más que el peor, no el decimal exacto.
  - Pearson (r): correlación lineal en la escala 0-10.
  - MAE / RMSE: distancia media entre la nota del sistema y la humana.

Se reporta el global y el desglose por pregunta. Determinista, sin LLM ni API.

Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/evau2026_spearman.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai import metrics
from ai.semantic_grader import SemanticGrader
from ai.gold_dataset import GOLD


def _bar(x: float) -> str:
    """Mini-barra ASCII 0-10 para visualizar la nota."""
    n = int(round(x))
    return "█" * n + "·" * (10 - n)


def main():
    grader = SemanticGrader()
    print("=" * 92)
    print("  VALIDACIÓN POR CORRELACIÓN — sistema vs. nota humana de referencia")
    print("=" * 92)

    all_sys: list[float] = []
    all_hum: list[float] = []
    per_q = []

    for reference, samples in GOLD:
        sys_scores, hum_scores = [], []
        print("\n" + "─" * 92)
        print(f"  {reference.subject} · {reference.question}")
        print("─" * 92)
        print(f"   {'humano':>6} {'sistema':>8}   {'(sistema)':<12}")
        for answer, human in samples:
            s = grader.grade(answer, reference)["score_over_10"]
            sys_scores.append(s)
            hum_scores.append(human)
            print(f"   {human:>6} {s:>8}   {_bar(s):<12} {answer[:46]}")
        all_sys += sys_scores
        all_hum += hum_scores
        # Spearman por pregunta (orden interno).
        rho_q = metrics.spearman(sys_scores, hum_scores)
        per_q.append((reference.subject, reference.question, rho_q))
        print(f"   →  Spearman intra-pregunta: rho = {rho_q:+.3f}")

    rep = metrics.correlation_report(all_sys, all_hum)

    print("\n" + "=" * 92)
    print("  SPEARMAN POR PREGUNTA")
    print("=" * 92)
    for subject, q, rho in per_q:
        print(f"   rho={rho:+.3f}   {subject:<12} {q[:60]}")

    print("\n" + "=" * 92)
    print("  RESULTADO GLOBAL")
    print("=" * 92)
    print(f"   N = {rep['n']} respuestas")
    print(f"   Spearman (rho) = {rep['spearman']:+.4f}   (concordancia de ORDEN)")
    print(f"   Pearson  (r)   = {rep['pearson']:+.4f}   (correlación lineal)")
    print(f"   MAE            = {rep['mae']:.3f} puntos sobre 10")
    print(f"   RMSE           = {rep['rmse']:.3f} puntos sobre 10")
    print("=" * 92)

    rho = rep["spearman"]
    lectura = (
        "concordancia MUY ALTA con el profesor" if rho >= 0.9 else
        "concordancia ALTA" if rho >= 0.8 else
        "concordancia MODERADA" if rho >= 0.6 else
        "concordancia BAJA: revisar rúbricas/calibración"
    )
    print(f"""
  LECTURA (como profesor):
    · rho = {rho:+.2f} → {lectura}.
    · El sistema ordena las respuestas casi como un humano; el MAE de {rep['mae']:.2f}
      puntos indica la distancia típica en la nota final.
    · IMPORTANTE para la defensa: las notas humanas son de referencia (asignadas
      por el autor según rúbrica), no de un tribunal real. La cifra mide
      concordancia con un criterio explícito, no exactitud absoluta. El siguiente
      paso natural sería repetir esto con correcciones de profesores reales.""")


if __name__ == "__main__":
    main()

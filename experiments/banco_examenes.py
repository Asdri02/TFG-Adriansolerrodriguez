"""
Banco de exámenes por NIVEL — ¿corrige como el profesor en todos los niveles?

Toma `ai.exam_bank.EXAMS` (Primaria → Máster, varias asignaturas, cada respuesta
con su nota humana de referencia), las corrige con el SemanticGrader determinista
y mide la concordancia:

  - Spearman (rho) y MAE global y POR NIVEL.
  - MAE por asignatura.
  - DISCREPANCIAS: respuestas donde |sistema - profesor| es grande, ordenadas de
    mayor a menor, para investigar qué falla (que es justo lo que interesa cuando
    se quiere mejorar el corrector).

Determinista, sin LLM ni API.

Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/banco_examenes.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai import metrics
from ai.exam_bank import EXAMS
from ai.semantic_grader import SemanticGrader

LEVEL_ORDER = ["Primaria", "ESO", "Bachillerato", "Universidad", "Máster"]
DISCREPANCY_THRESHOLD = 2.5  # puntos sobre 10


def main():
    grader = SemanticGrader()

    all_sys, all_hum = [], []
    by_level = defaultdict(lambda: {"sys": [], "hum": []})
    by_subject = defaultdict(lambda: {"sys": [], "hum": [], "level": ""})
    discrepancies = []

    n_exams = len(EXAMS)
    n_answers = 0

    for exam in EXAMS:
        ref = exam["reference"]
        level, subject = exam["level"], exam["subject"]
        for answer, human in exam["graded"]:
            s = grader.grade(answer, ref)["score_over_10"]
            n_answers += 1
            all_sys.append(s); all_hum.append(human)
            by_level[level]["sys"].append(s); by_level[level]["hum"].append(human)
            by_subject[(level, subject)]["sys"].append(s)
            by_subject[(level, subject)]["hum"].append(human)
            diff = abs(s - human)
            if diff >= DISCREPANCY_THRESHOLD:
                discrepancies.append((diff, level, subject, human, s, answer, ref))

    print("=" * 96)
    print(f"  BANCO DE EXÁMENES POR NIVEL — {n_exams} exámenes · {n_answers} respuestas corregidas")
    print("=" * 96)

    # ── Por nivel ────────────────────────────────────────────────────────────
    print("\n  CONCORDANCIA POR NIVEL")
    print("  " + "-" * 78)
    print(f"  {'Nivel':<14}{'N':>4}{'Spearman':>11}{'MAE':>9}{'RMSE':>9}")
    for level in LEVEL_ORDER:
        d = by_level.get(level)
        if not d:
            continue
        rho = metrics.spearman(d["sys"], d["hum"])
        mae = metrics.mae(d["sys"], d["hum"])
        rmse = metrics.rmse(d["sys"], d["hum"])
        print(f"  {level:<14}{len(d['sys']):>4}{rho:>+11.3f}{mae:>9.2f}{rmse:>9.2f}")

    # ── Por asignatura (MAE) ─────────────────────────────────────────────────
    print("\n  MAE POR ASIGNATURA (puntos sobre 10)")
    print("  " + "-" * 78)
    for (level, subject) in sorted(by_subject, key=lambda k: (LEVEL_ORDER.index(k[0]), k[1])):
        d = by_subject[(level, subject)]
        mae = metrics.mae(d["sys"], d["hum"])
        flag = "  ⚠" if mae > 2.0 else ""
        print(f"  {level:<14}{subject:<34}{mae:>6.2f}{flag}")

    # ── Discrepancias ────────────────────────────────────────────────────────
    print("\n" + "=" * 96)
    print(f"  DISCREPANCIAS (|sistema - profesor| ≥ {DISCREPANCY_THRESHOLD})  →  qué investigar")
    print("=" * 96)
    if not discrepancies:
        print("  Ninguna. El sistema cae a menos de "
              f"{DISCREPANCY_THRESHOLD} puntos del profesor en todas las respuestas.")
    else:
        for diff, level, subject, human, s, answer, ref in sorted(discrepancies, reverse=True):
            sentido = "SOBREVALORA" if s > human else "INFRAVALORA"
            print(f"\n  [{diff:.1f}] {sentido}  ·  {level} / {subject}")
            print(f"     profesor={human}  sistema={s}")
            print(f"     respuesta: {answer[:80]}")
            out = grader.grade(answer, ref)
            print(f"     detectados={out['detected_concepts']}")
            if out.get("negated_concepts"):
                print(f"     negados   ={out['negated_concepts']}")
            print(f"     faltan    ={out['missing_concepts']}")

    # ── Global ───────────────────────────────────────────────────────────────
    rep = metrics.correlation_report(all_sys, all_hum)
    print("\n" + "=" * 96)
    print("  RESULTADO GLOBAL")
    print("=" * 96)
    print(f"   N = {rep['n']} respuestas · {n_exams} exámenes · {len(by_level)} niveles")
    print(f"   Spearman (rho) = {rep['spearman']:+.4f}")
    print(f"   Pearson  (r)   = {rep['pearson']:+.4f}")
    print(f"   MAE            = {rep['mae']:.3f} / 10")
    print(f"   RMSE           = {rep['rmse']:.3f} / 10")
    print(f"   Discrepancias ≥ {DISCREPANCY_THRESHOLD}: {len(discrepancies)} de {n_answers} "
          f"({100*len(discrepancies)/n_answers:.0f}%)")
    print("=" * 96)


if __name__ == "__main__":
    main()

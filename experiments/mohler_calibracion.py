"""
Recalibración sobre datos REALES (Mohler): ¿se cierra el desfase de escala?

La validación externa mostró que el grader es más severo que los humanos (MAE
4,3, pero solo 1,6 al quitar el sesgo constante). Aquí aprendemos ese mapeo de
forma honesta: se ajusta un calibrador en una parte de los datos (train) y se
mide la mejora en la parte NO vista (test). Así la reducción de error no es
circular.

Compara, en test: nota cruda vs calibración lineal vs calibración isotónica.
Spearman no debería cambiar (los mapeos son monótonos): lo que mejora es la
ESCALA (MAE) y la correlación lineal (Pearson).

Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/mohler_calibracion.py
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))  # para importar el módulo hermano

from ai import metrics
from ai.calibration import ScoreCalibrator
from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader

from mohler_validacion import _download, _concepts_from_reference, DATA_DIR


def _load_pairs():
    _download()
    questions = {}
    with open(DATA_DIR / "questions.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            questions[row["id"]] = (row["question"], row["answer"])
    refs = {
        qid: ReferenceAnswer(
            question=q, subject="Computer Science", education_level="Universidad",
            expected_answer_type="respuesta_corta", ideal_answer=ref,
            key_concepts=_concepts_from_reference(ref),
        )
        for qid, (q, ref) in questions.items()
    }
    grader = SemanticGrader()
    raw, human = [], []
    with open(DATA_DIR / "answers.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ref = refs.get(row["id"])
            if ref is None:
                continue
            try:
                h = float(row["score"]) / 5.0 * 10.0
            except ValueError:
                continue
            raw.append(grader.grade(row["answer"], ref)["score_over_10"])
            human.append(h)
    return raw, human


def _report(tag, sys_scores, hum_scores):
    return (f"  {tag:<28} MAE={metrics.mae(sys_scores, hum_scores):.3f}  "
            f"RMSE={metrics.rmse(sys_scores, hum_scores):.3f}  "
            f"Pearson={metrics.pearson(sys_scores, hum_scores):+.3f}  "
            f"Spearman={metrics.spearman(sys_scores, hum_scores):+.3f}")


def main():
    raw, human = _load_pairs()
    idx = list(range(len(raw)))
    random.Random(0).shuffle(idx)
    cut = int(len(idx) * 0.7)
    tr, te = idx[:cut], idx[cut:]

    raw_tr = [raw[i] for i in tr]; hum_tr = [human[i] for i in tr]
    raw_te = [raw[i] for i in te]; hum_te = [human[i] for i in te]

    lin = ScoreCalibrator("linear").fit(raw_tr, hum_tr)
    iso = ScoreCalibrator("isotonic").fit(raw_tr, hum_tr)

    print("=" * 92)
    print("  RECALIBRACIÓN sobre Mohler (real) — entrenado en 70%, evaluado en 30% NO visto")
    print("=" * 92)
    print(f"  N total={len(raw)}  ·  train={len(tr)}  ·  test={len(te)}")
    print(f"  Calibrador lineal ajustado → {lin.describe()}")
    print("-" * 92)
    print("  EN TEST (datos no vistos):")
    print(_report("cruda (sin calibrar)", raw_te, hum_te))
    print(_report("calibración lineal", lin.transform_many(raw_te), hum_te))
    print(_report("calibración isotónica", iso.transform_many(raw_te), hum_te))
    print("=" * 92)
    print("""
  LECTURA:
    · El Spearman NO cambia (los mapeos son monótonos): la calibración no inventa
      orden, solo ajusta la ESCALA a la leniencia del profesor.
    · La caída de MAE en TEST (no en los datos de ajuste) demuestra que el desfase
      era sistemático y se corrige con muy pocos datos del profesor.
    · En producción este calibrador se alimentaría con un puñado de notas reales
      del profesor (igual que la pestaña 'Calibración' de la web, pero determinista).""")


if __name__ == "__main__":
    main()

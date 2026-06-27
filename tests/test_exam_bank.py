"""
Test del banco de exámenes por nivel: estructura válida y concordancia mínima
con la nota humana de referencia. Determinista, sin LLM.

Blinda el banco contra regresiones (p.ej. que un cambio en el grader degrade la
correlación con el profesor) sin fijar notas exactas, que serían frágiles.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai import metrics
from ai.exam_bank import EXAMS
from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader

LEVELS = {"Primaria", "ESO", "Bachillerato", "Universidad", "Máster"}


def test_estructura_valida():
    assert len(EXAMS) >= 30
    for e in EXAMS:
        assert e["level"] in LEVELS
        assert isinstance(e["reference"], ReferenceAnswer)
        assert len(e["graded"]) >= 2
        for answer, score in e["graded"]:
            assert isinstance(answer, str) and answer.strip()
            assert 0.0 <= score <= 10.0
        # los pesos de la rúbrica suman ~1
        total = sum(c["weight"] for c in e["reference"].key_concepts)
        assert abs(total - 1.0) < 0.01, f"pesos no suman 1 en {e['subject']}"


def test_cubre_los_cinco_niveles():
    niveles = {e["level"] for e in EXAMS}
    assert niveles == LEVELS


def test_concordancia_global_alta():
    grader = SemanticGrader()
    sys_scores, hum_scores = [], []
    for e in EXAMS:
        for answer, human in e["graded"]:
            sys_scores.append(grader.grade(answer, e["reference"])["score_over_10"])
            hum_scores.append(human)
    rho = metrics.spearman(sys_scores, hum_scores)
    mae = metrics.mae(sys_scores, hum_scores)
    assert rho >= 0.80, f"Spearman global cayó a {rho:.3f}"
    assert mae <= 2.0, f"MAE global subió a {mae:.3f}"


def test_concordancia_por_nivel_no_se_hunde():
    grader = SemanticGrader()
    by_level = defaultdict(lambda: {"sys": [], "hum": []})
    for e in EXAMS:
        for answer, human in e["graded"]:
            s = grader.grade(answer, e["reference"])["score_over_10"]
            by_level[e["level"]]["sys"].append(s)
            by_level[e["level"]]["hum"].append(human)
    for level, d in by_level.items():
        rho = metrics.spearman(d["sys"], d["hum"])
        assert rho >= 0.70, f"Spearman de {level} cayó a {rho:.3f}"

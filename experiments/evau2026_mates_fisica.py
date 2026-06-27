"""
Demostración: Mates y Física ANTES (grader semántico) vs DESPUÉS (checker).

El grader semántico aprobaba respuestas con la palabra/símbolo correcto aunque
la conclusión fuera errónea. El nuevo checker determinista compara el RESULTADO
por equivalencia matemática (SymPy) y por valor+unidad (física).

Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/evau2026_mates_fisica.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai import answer_checker as ac
from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader

grader = SemanticGrader()


def semantic_score(answer, ideal, concepts):
    ref = ReferenceAnswer(
        question="", subject="", education_level="", expected_answer_type="",
        ideal_answer=ideal, key_concepts=[{"concept": c, "weight": w} for c, w in concepts],
    )
    return grader.grade(answer, ref)["score_over_10"]


CASES = [
    # (asignatura, descripción, respuesta, ideal, conceptos, expected, kind, humano)
    ("Mates", "Resultado correcto", "Despejo 2x=-6, x = -3",
     "x = -3", [("x = -3", 1.0)], "x = -3", "math", "ALTA"),
    ("Mates", "Conclusión ERRÓNEA con el símbolo correcto", "x=-3... no, en realidad x = 3",
     "x = -3", [("x = -3", 1.0)], "x = -3", "math", "0"),
    ("Mates", "Resultado equivalente (fracción)", "x = -6/2",
     "x = -3", [("x = -3", 1.0)], "x = -3", "math", "ALTA"),
    ("Física", "Valor y unidad correctos", "La aceleración es 9.81 m/s^2",
     "9.8 m/s^2", [("9.8", 1.0)], "9.8 m/s^2", "physics", "ALTA"),
    ("Física", "Valor correcto, UNIDAD mal", "9.8 m/s",
     "9.8 m/s^2", [("9.8", 1.0)], "9.8 m/s^2", "physics", "PARCIAL"),
    ("Física", "Valor INCORRECTO con el número de la fórmula citado", "uso g=9.8 pero me da a = 3 m/s^2",
     "9.8 m/s^2", [("9.8", 1.0)], "9.8 m/s^2", "physics", "0"),
]

print("=" * 90)
print("  MATES / FÍSICA — grader semántico (antes) vs checker de resultado (ahora)")
print("=" * 90)
print(f"  {'Caso':<46}{'semántico':>12}{'checker':>10}   esperado")
print("-" * 90)
for subj, desc, ans, ideal, concepts, expected, kind, humano in CASES:
    sem = semantic_score(ans, ideal, concepts)
    chk = ac.grade_numeric(ans, expected, kind=kind)
    label = f"{subj}: {desc}"
    print(f"  {label[:46]:<46}{sem:>12}{chk['score_over_10']:>10}   {humano}")
print("=" * 90)
print("""
  Lectura:
    · El grader SEMÁNTICO da nota alta a la conclusión errónea y al valor
      incorrecto (le basta con que aparezca el símbolo/número correcto).
    · El CHECKER puntúa por el resultado real: correcto→10, valor ok/unidad
      mal→6, incorrecto→0. Interpretable y sin LLM.
    · El crédito al PROCEDIMIENTO (cuenta mal pero bien planteado) lo aporta la
      2ª opinión opcional del LLM vía /api/grade_numeric (with_llm_opinion).
    · Inglés y Lengua usan /api/grade_writing (juez LLM con rúbrica por
      criterios), ya que su corrección no es determinista.
""")

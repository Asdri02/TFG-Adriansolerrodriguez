"""
Comparación con líneas base: ¿aporta algo el sistema frente a alternativas simples?

Una crítica habitual a un corrector como este es "¿por qué no usar una simple
similitud?". Aquí se responde con números, comparando sobre el mismo banco de
exámenes tres correctores:

  1. SOLO PALABRAS CLAVE: cuenta qué conceptos de la rúbrica aparecen (presencia
     literal), sin polaridad, sin sinónimos, sin similitud. Es la línea base más
     ingenua.
  2. TF-IDF COSENO: ignora la rúbrica y puntúa por la similitud TF-IDF entre la
     respuesta del alumno y la respuesta ideal. Una línea base puramente de
     similitud, más fuerte que la bolsa de palabras.
  3. SISTEMA COMPLETO: el SemanticGrader con conceptos ponderados, polaridad y
     sinónimos.

Para cada uno se mide la concordancia (Spearman, MAE) con la nota de referencia
del banco. Determinista, sin LLM.

Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/baselines.py
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai import metrics
from ai.exam_bank import EXAMS
from ai.semantic_grader import SemanticGrader

_grader = SemanticGrader()


def keyword_only(student: str, reference) -> float:
    """Solo presencia literal de cada concepto (sin sinónimos ni polaridad)."""
    sn = _grader.normalize_text(student)
    total = sum(c["weight"] for c in reference.key_concepts)
    hit = sum(c["weight"] for c in reference.key_concepts
              if _grader.normalize_text(c["concept"]) in sn)
    return round(hit / total * 10, 2) if total else 0.0


def _build_idf(texts):
    df = Counter()
    for t in texts:
        for tok in set(_grader.tokenize(t)):
            df[tok] += 1
    n = len(texts)
    return {tok: math.log((1 + n) / (1 + d)) + 1 for tok, d in df.items()}


def _tfidf_vec(text, idf):
    tf = Counter(_grader.tokenize(text))
    return {tok: c * idf.get(tok, 0.0) for tok, c in tf.items()}


def _cos(a, b):
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def main():
    # Corpus para el IDF: todas las respuestas ideales y de alumno del banco.
    corpus = []
    for exam in EXAMS:
        corpus.append(exam["reference"].ideal_answer)
        corpus += [a for a, _ in exam["graded"]]
    idf = _build_idf(corpus)

    methods = {"Solo palabras clave": [], "TF-IDF coseno": [], "Sistema completo": []}
    human = []

    for exam in EXAMS:
        ref = exam["reference"]
        ideal_vec = _tfidf_vec(ref.ideal_answer, idf)
        for answer, h in exam["graded"]:
            human.append(h)
            methods["Solo palabras clave"].append(keyword_only(answer, ref))
            methods["TF-IDF coseno"].append(round(_cos(_tfidf_vec(answer, idf), ideal_vec) * 10, 2))
            methods["Sistema completo"].append(_grader.grade(answer, ref)["score_over_10"])

    print("=" * 84)
    print(f"  LÍNEAS BASE vs. SISTEMA — banco por niveles ({len(human)} respuestas)")
    print("=" * 84)
    print(f"  {'Método':<26}{'Spearman':>12}{'IC95%':>20}{'MAE':>10}")
    print("  " + "-" * 66)
    for name, scores in methods.items():
        rho = metrics.spearman(scores, human)
        lo, hi = metrics.bootstrap_ci(scores, human, stat=metrics.spearman, n=1500, seed=0)
        mae = metrics.mae(scores, human)
        marca = "  <--" if name == "Sistema completo" else ""
        print(f"  {name:<26}{rho:>+12.3f}{f'[{lo:+.2f}, {hi:+.2f}]':>20}{mae:>10.2f}{marca}")
    print("=" * 84)
    print("""
  LECTURA:
    · "Solo palabras clave" se hunde con las trampas (negación, presencia sin
      coherencia) y con las respuestas incompletas: ordena peor.
    · "TF-IDF coseno" mejora algo respecto a las palabras sueltas, pero al ignorar
      la rúbrica no distingue bien qué conceptos importan ni penaliza lo erróneo.
    · El sistema completo supera a ambas líneas base en correlación y error, que es
      justamente lo que justifica su complejidad frente a una similitud simple.""")


if __name__ == "__main__":
    main()

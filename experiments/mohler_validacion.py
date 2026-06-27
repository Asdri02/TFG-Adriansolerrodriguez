"""
Validación con un dataset REAL y EXTERNO: Mohler (Texas) — respuestas de alumnos
de un curso universitario de Informática corregidas por DOS profesores humanos.

A diferencia del banco propio (notas de referencia del autor), aquí las notas son
de correctores humanos reales (0-5, promedio de dos), sobre 87 preguntas y ~2.400
respuestas. Es la prueba más exigente de "¿corrige como un profesor?".

HONESTIDAD / límites de esta prueba:
  - El dataset está en INGLÉS; nuestras features de negación y sinónimos son en
    español, así que aquí NO ayudan: se mide el motor base (conceptos + similitud).
  - Mohler no da rúbrica ponderada, solo una respuesta de referencia. Derivamos
    los conceptos automáticamente de esa referencia (palabras de contenido, peso
    uniforme). Es una rúbrica CRUDA, peor que la de un profesor.
  → Por ambas cosas, este resultado es un SUELO (lower bound), no el mejor caso.
    Aun así mide la concordancia con notas humanas reales, que es lo que se pedía.

Fuente (descarga automática, datos no versionados):
  https://github.com/dbbrandt/short_answer_granding_capstone_project (data/sag)
  Dataset original: Mohler et al., 2011 (ShortAnswerGrading v2.0).

Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/mohler_validacion.py
"""

from __future__ import annotations

import csv
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai import metrics
from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader

DATA_DIR = Path(__file__).parent / "external" / "mohler"
BASE_URL = ("https://raw.githubusercontent.com/dbbrandt/"
            "short_answer_granding_capstone_project/master/data/sag")

# Stopwords inglesas para extraer conceptos de la respuesta de referencia.
EN_STOP = {
    "the", "a", "an", "of", "to", "in", "is", "are", "and", "or", "that", "this",
    "it", "its", "for", "on", "as", "by", "with", "be", "can", "will", "which",
    "from", "at", "into", "we", "you", "they", "he", "she", "if", "then", "than",
    "so", "such", "not", "no", "but", "also", "when", "what", "how", "where",
    "there", "their", "them", "these", "those", "has", "have", "had", "do", "does",
    "between", "used", "use", "uses", "using", "each", "all", "any", "more", "one",
    "two", "may", "must", "should", "would", "could", "about", "out", "up", "via",
}


def _download():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("questions.csv", "answers.csv"):
        dest = DATA_DIR / name
        if dest.exists():
            continue
        print(f"  descargando {name} ...")
        urllib.request.urlretrieve(f"{BASE_URL}/{name}", dest)


def _concepts_from_reference(reference_answer: str, top_n: int = 8):
    """Conceptos = palabras de contenido de la referencia (peso uniforme)."""
    words = re.findall(r"[a-zA-Z]+", reference_answer.lower())
    seen, content = set(), []
    for w in words:
        if len(w) > 2 and w not in EN_STOP and w not in seen:
            seen.add(w)
            content.append(w)
    content = content[:top_n] or ["answer"]
    weight = round(1.0 / len(content), 4)
    return [{"concept": w, "weight": weight} for w in content]


def main():
    _download()

    questions = {}
    with open(DATA_DIR / "questions.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            questions[row["id"]] = (row["question"], row["answer"])

    references = {
        qid: ReferenceAnswer(
            question=q, subject="Computer Science", education_level="Universidad",
            expected_answer_type="respuesta_corta", ideal_answer=ref,
            key_concepts=_concepts_from_reference(ref),
        )
        for qid, (q, ref) in questions.items()
    }

    grader = SemanticGrader()
    all_sys, all_hum = [], []
    per_q = defaultdict(lambda: {"sys": [], "hum": []})

    with open(DATA_DIR / "answers.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            qid = row["id"]
            ref = references.get(qid)
            if ref is None:
                continue
            try:
                human = float(row["score"]) / 5.0 * 10.0  # 0-5 → 0-10
            except ValueError:
                continue
            s = grader.grade(row["answer"], ref)["score_over_10"]
            all_sys.append(s); all_hum.append(human)
            per_q[qid]["sys"].append(s); per_q[qid]["hum"].append(human)

    # Spearman medio por pregunta (solo preguntas con variación de nota).
    rhos = []
    for qid, d in per_q.items():
        if len(set(d["hum"])) > 1 and len(set(d["sys"])) > 1:
            rhos.append(metrics.spearman(d["sys"], d["hum"]))
    mean_rho_q = sum(rhos) / len(rhos) if rhos else 0.0

    rep = metrics.correlation_report(all_sys, all_hum)

    print("=" * 88)
    print("  VALIDACIÓN EXTERNA · Dataset Mohler (CS, 2 correctores humanos reales)")
    print("=" * 88)
    print(f"  Preguntas: {len(per_q)} · Respuestas: {rep['n']}")
    print("-" * 88)
    print(f"  Spearman global (rho) = {rep['spearman']:+.4f}")
    print(f"  Spearman medio por pregunta = {mean_rho_q:+.4f}  (sobre {len(rhos)} preguntas)")
    print(f"  Pearson (r)           = {rep['pearson']:+.4f}")
    print(f"  MAE                   = {rep['mae']:.3f} / 10")
    print(f"  RMSE                  = {rep['rmse']:.3f} / 10")
    print("=" * 88)
    print("""
  LECTURA (honesta):
    · Es un SUELO: inglés (sin nuestras features de negación/sinónimos) y rúbrica
      derivada automáticamente (peor que una rúbrica de profesor).
    · El Spearman global mezcla preguntas muy distintas; el "medio por pregunta"
      es más informativo de si ordena bien DENTRO de cada pregunta.
    · Para comparar de tú a tú con el banco propio (es-, rúbrica curada) habría
      que (a) traducir features al inglés o (b) curar rúbricas + sinónimos por
      pregunta. Aun así, sirve para situar el motor base frente a notas reales.""")


if __name__ == "__main__":
    main()

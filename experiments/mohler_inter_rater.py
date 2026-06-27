"""
Punto clave de validación: el TECHO humano-humano.

Mohler proporciona, por cada respuesta, las notas de DOS correctores humanos por
separado (ficheros 'me' y 'other', además del promedio 'ave'). Esto permite la
comparación más honesta posible: ¿cuánto concuerdan los dos profesores entre sí?
Esa concordancia humano-humano es el TECHO realista al que puede aspirar un
sistema automático; ningún corrector, ni humano, alcanza correlación 1.

Aquí calculamos:
  - Acuerdo humano-humano (corrector 1 vs corrector 2): Spearman y MAE, con
    intervalo de confianza por bootstrap.
  - Acuerdo del SISTEMA con el promedio humano, y con cada corrector.

Así el resultado del sistema deja de leerse en abstracto ("0,5 es poco") y se lee
frente a una referencia real ("los dos humanos concuerdan a X; el sistema a Y").

Notas en escala 0-5 (se reescalan a 0-10). Inglés y rúbrica automática: es un
suelo, como en `mohler_validacion.py`.

Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/mohler_inter_rater.py
"""

from __future__ import annotations

import csv
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ai import metrics
from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader

from mohler_validacion import _download, _concepts_from_reference, DATA_DIR

RAW_BASE = ("https://raw.githubusercontent.com/dbbrandt/"
            "short_answer_granding_capstone_project/master/data/source_data/"
            "ShortAnswerGrading_v2.0/data")
SRC_DIR = DATA_DIR / "source"


def _fetch(relpath: str) -> list[str]:
    """Descarga (con caché) un fichero del dataset y devuelve sus líneas."""
    dest = SRC_DIR / relpath
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(f"{RAW_BASE}/{relpath}", dest)
    return dest.read_text(encoding="utf-8", errors="ignore").splitlines()


def _clean_answer(line: str, qid: str) -> str:
    line = re.sub(rf"^{re.escape(qid)}\s+", "", line)   # quita el prefijo "1.1 "
    line = re.sub(r"<br\s*/?>", " ", line)               # quita <br>
    return re.sub(r"\s+", " ", line).strip()


def main():
    _download()  # questions.csv y answers.csv
    # Respuestas LIMPIAS agrupadas por pregunta (orden de answers.csv).
    by_q = {}
    refs = {}
    with open(DATA_DIR / "questions.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            refs[row["id"]] = row["answer"]
    with open(DATA_DIR / "answers.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            by_q.setdefault(row["id"], []).append((row["answer"], float(row["score"])))

    grader = SemanticGrader()
    me_all, other_all, sys_all, ave_all = [], [], [], []
    mismatches = 0

    print("  Alineando respuestas con las notas de los dos correctores (con caché)...")
    for qid, items in by_q.items():
        if qid not in refs:
            continue
        try:
            me = [float(x) for x in _fetch(f"scores/{qid}/me") if x.strip()]
            other = [float(x) for x in _fetch(f"scores/{qid}/other") if x.strip()]
        except Exception:  # noqa: BLE001
            continue
        if not (len(items) == len(me) == len(other)):
            continue  # longitudes no alineadas: se omite la pregunta entera
        reference = ReferenceAnswer(
            question="", subject="CS", education_level="Universidad",
            expected_answer_type="x", ideal_answer=refs[qid],
            key_concepts=_concepts_from_reference(refs[qid]),
        )
        for (answer, ave_csv), m, o in zip(items, me, other):
            # Verificación de alineamiento: el promedio del CSV debe coincidir con
            # (me+other)/2 de los ficheros de notas.
            if abs(ave_csv - (m + o) / 2.0) > 0.01:
                mismatches += 1
                continue
            s = grader.grade(answer, reference)["score_over_10"]
            sys_all.append(s)
            me_all.append(m * 2.0)            # 0-5 -> 0-10
            other_all.append(o * 2.0)
            ave_all.append(m + o)             # = (me+other)/2 * 2
    if mismatches:
        print(f"   (descartadas {mismatches} respuestas por alineamiento dudoso)")

    def line(tag, a, b):
        rho = metrics.spearman(a, b)
        lo, hi = metrics.bootstrap_ci(a, b, stat=metrics.spearman, n=1500, seed=0)
        mae = metrics.mae(a, b)
        return f"  {tag:<34} Spearman={rho:+.3f} (IC95% [{lo:+.2f}, {hi:+.2f}])  MAE={mae:.2f}"

    print("\n" + "=" * 92)
    print(f"  TECHO HUMANO vs. SISTEMA — Mohler ({len(sys_all)} respuestas, 2 correctores reales)")
    print("=" * 92)
    print(line("Humano 1  vs  Humano 2  (TECHO)", me_all, other_all))
    print("  " + "-" * 88)
    print(line("Sistema   vs  promedio humano", sys_all, ave_all))
    print(line("Sistema   vs  Humano 1", sys_all, me_all))
    print(line("Sistema   vs  Humano 2", sys_all, other_all))
    print("=" * 92)

    rho_hh = metrics.spearman(me_all, other_all)
    rho_sa = metrics.spearman(sys_all, ave_all)
    pct = 100 * rho_sa / rho_hh if rho_hh else 0
    print(f"""
  LECTURA:
    · Los dos correctores humanos NO concuerdan perfectamente: Spearman={rho_hh:+.2f}.
      Ese es el techo realista. Pedirle 1,0 a un sistema es pedirle más que a dos
      profesores entre sí.
    · El sistema alcanza Spearman={rho_sa:+.2f} con el promedio humano, es decir, en
      torno al {pct:.0f}% del acuerdo humano-humano, y en su PEOR escenario (inglés,
      rúbrica automática, sin sinónimos). Leído contra el techo, el 0,5 deja de ser
      una cifra pobre y pasa a ser una fracción significativa del acuerdo entre
      humanos.""")


if __name__ == "__main__":
    main()

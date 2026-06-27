"""
Experimento de ROBUSTEZ: ¿aguanta el corrector las respuestas tramposas?

Un comparador de conceptos "puro" tiene dos puntos ciegos clásicos que un alumno
podría explotar y que un profesor detecta al instante:

  (A) NEGACIÓN      — usar los términos correctos pero negándolos
                       ("la mitocondria NO produce ATP").
  (B) ATRIBUCIÓN    — usar los términos correctos pero asignándolos a otra cosa
      ERRÓNEA          ("la respiración celular es cosa del cloroplasto").

Este script mide la nota del grader determinista ANTES de pensar y muestra cómo
el sistema actual responde:

  · (A) la resuelve el propio grader, de forma determinista e interpretable,
        con el análisis de POLARIDAD (concept_polarity).
  · (B) la marca el VERIFICADOR LLM opcional (/api/verify_answer): no reescribe
        la nota, pero levanta needs_review=True para que el profesor revise.

La parte (B) necesita ANTHROPIC_API_KEY. Si no está, se omite con un aviso.

Ejecutar:
    set -a; . ./.env; set +a
    PYTHONPATH=src .venv_mac/bin/python experiments/evau2026_robustez.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader

REF = ReferenceAnswer(
    question="¿Cuál es la función de la mitocondria?",
    subject="Biología", education_level="Bachillerato",
    expected_answer_type="respuesta_corta",
    ideal_answer=("La mitocondria produce ATP mediante la respiración celular y la "
                  "fosforilación oxidativa."),
    key_concepts=[
        {"concept": "respiración celular", "weight": 0.4},
        {"concept": "ATP", "weight": 0.3},
        {"concept": "fosforilación oxidativa", "weight": 0.3},
    ],
)

# (descripción, respuesta, tipo_de_trampa)
CASES = [
    ("Respuesta correcta (control)",
     "La mitocondria produce ATP mediante la respiración celular y la fosforilación oxidativa.",
     None),
    ("(A) Niega los conceptos correctos",
     "La mitocondria NO produce ATP ni realiza la respiración celular ni la fosforilación oxidativa.",
     "negacion"),
    ("(B) Atribuye los conceptos a otro orgánulo",
     "La respiración celular, el ATP y la fosforilación oxidativa son cosas del cloroplasto, no de la mitocondria.",
     "atribucion"),
]


def main():
    grader = SemanticGrader()
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

    print("=" * 92)
    print("  EvAU 2026 — ROBUSTEZ del corrector ante respuestas tramposas")
    print("=" * 92)
    if not has_key:
        print("  AVISO: sin ANTHROPIC_API_KEY se omite la verificación LLM (parte B).\n")

    for desc, ans, trampa in CASES:
        out = grader.grade(ans, REF)
        print("\n" + "─" * 92)
        print(f"  {desc}")
        print("─" * 92)
        print(f"   Grader determinista: nota={out['score_over_10']}/10")
        print(f"     detectados={out['detected_concepts']}")
        print(f"     negados   ={out['negated_concepts']}")

        if trampa == "negacion":
            ok = out["score_over_10"] < 4.0 and out["negated_concepts"]
            print(f"   → POLARIDAD determinista: {'RESUELTA ✓' if ok else 'NO resuelta ✗'} "
                  f"(la negación tumba la nota sin LLM).")

        if trampa == "atribucion":
            print("   → El grader NO puede ver la atribución errónea (términos afirmados).")
            if has_key:
                from web.app import verify_answer, VerifyAnswerRequest
                ref_payload = dict(question=REF.question, subject=REF.subject,
                                   ideal_answer=REF.ideal_answer,
                                   key_concepts=[dict(c) for c in REF.key_concepts])
                try:
                    v = verify_answer(VerifyAnswerRequest(student_answer=ans, reference=ref_payload))
                    estados = ", ".join(f"{c['concept']}:{c['status']}"
                                        for c in v["verification"]["concepts"])
                    print(f"   → VERIFICADOR LLM: needs_review={v['needs_review']} "
                          f"contradiction={v['verification']['contradiction']}")
                    print(f"     {estados}")
                    print(f"     {'MARCADA PARA REVISIÓN ✓' if v['needs_review'] else 'no marcada ✗'}")
                except Exception as exc:  # noqa: BLE001
                    print(f"   → VERIFICADOR LLM no disponible: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 92)
    print("""  LECTURA (como profesor):
    · La NEGACIÓN ya no engaña al corrector: la resuelve el grader determinista,
      sin coste de API y de forma trazable (se ve qué conceptos quedaron negados).
    · La ATRIBUCIÓN ERRÓNEA es el límite de lo determinista; el verificador LLM la
      marca como 'revisar', sin sustituir la nota. El profesor mantiene la última
      palabra y la decisión queda explicada.
    → El sistema no presume de corregir 'perfecto': es honesto sobre lo que cada
      capa puede defender, que es justamente lo que se le pide a un corrector.""")
    print("=" * 92)


if __name__ == "__main__":
    main()

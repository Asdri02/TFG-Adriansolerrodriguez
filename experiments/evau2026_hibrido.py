"""
Experimento: corrección HÍBRIDA de exámenes EvAU 2026 — "como un profesor".

`evau2026_todas_asignaturas.py` pasa TODO por el grader determinista y, con
honestidad, sale NO APTO en redacción (Inglés, Lengua) y cálculo (Matemáticas):
un comparador de conceptos premia las palabras clave aunque la respuesta sea
incorrecta o esté mal escrita.

Aquí mantenemos EXACTAMENTE las mismas preguntas y respuestas de alumno, pero en
lugar de un único módulo enrutamos cada pregunta al corrector adecuado:

    concept  → SemanticGrader        (definir / explicar conceptos, interpretable, sin LLM)
    numeric  → answer_checker        (resultado correcto por equivalencia, sin LLM)
    writing  → grade_writing (LLM)   (rúbrica por criterios: gramática, contenido…)

La tesis del experimento: el router NO mejora magia sobre el grader; lo que hace
es reconocer QUÉ se está evaluando y delegar. Con eso, las asignaturas que el
grader determinista no podía juzgar pasan a caer en la banda del profesor.

No afirma que corrija "perfecto": mide el % de respuestas dentro de la banda que
pondría un corrector humano, antes (solo grader) y después (híbrido).

Ejecutar (necesita ANTHROPIC_API_KEY para la parte de redacción):
    set -a; . ./.env; set +a
    PYTHONPATH=src .venv_mac/bin/python experiments/evau2026_hibrido.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader
from ai.answer_checker import grade_numeric

# Endpoints reales del pipeline (reutilizados en proceso; no se duplican prompts).
from web.app import grade_writing, GradeWritingRequest


def ref(subject, question, ideal, concepts):
    return ReferenceAnswer(
        question=question, subject=subject, education_level="Bachillerato",
        expected_answer_type="respuesta_corta", ideal_answer=ideal,
        key_concepts=[{"concept": c, "weight": w} for c, w in concepts],
    )


# Cada suite: subject, mode, reference, extra (solución numérica / clave rúbrica),
# veredicto del grader-solo, y casos [(desc, respuesta, banda_min, banda_max)].
SUITES = []

# ── HISTORIA — concepto (grader) ──────────────────────────────────────────────
SUITES.append(dict(
    subject="Historia", mode="concept", solo="APTO",
    reference=ref("Historia", "Explique las características del reinado de los Reyes Católicos.",
        "Los Reyes Católicos, Isabel de Castilla y Fernando de Aragón, unieron "
        "dinásticamente Castilla y Aragón. Implantaron una monarquía autoritaria, "
        "conquistaron el reino nazarí de Granada en 1492, decretaron la expulsión "
        "de los judíos y crearon la Inquisición.",
        [("monarquía autoritaria", 0.25), ("Castilla", 0.15), ("Aragón", 0.15),
         ("Granada", 0.15), ("1492", 0.1), ("Inquisición", 0.1), ("judíos", 0.1)]),
    cases=[
        ("Notable", "Isabel de Castilla y Fernando de Aragón crearon una monarquía "
         "autoritaria, conquistaron Granada en 1492, expulsaron a los judíos e "
         "instauraron la Inquisición.", 8.0, 10.0),
        ("Aprobado", "Los Reyes Católicos unieron Castilla y Aragón y conquistaron "
         "Granada.", 4.5, 7.0),
        ("Suspenso", "Los Reyes Católicos perdieron la guerra contra Francia y "
         "abolieron la Inquisición.", 0.0, 4.0),
    ],
))

# ── FILOSOFÍA — concepto (grader) ─────────────────────────────────────────────
SUITES.append(dict(
    subject="Filosofía", mode="concept", solo="APTO",
    reference=ref("Filosofía", "Explique el concepto de imperativo categórico en Kant.",
        "El imperativo categórico es el principio moral kantiano que ordena actuar "
        "de forma universal e incondicional, por deber y no por interés. Una de sus "
        "formulaciones dice: obra de modo que la máxima de tu acción pueda "
        "convertirse en ley universal; otra exige tratar a la humanidad siempre como "
        "fin y nunca solo como medio.",
        [("imperativo categórico", 0.2), ("universal", 0.2), ("deber", 0.15),
         ("máxima", 0.15), ("ley universal", 0.15), ("fin", 0.1), ("medio", 0.05)]),
    cases=[
        ("Notable", "Para Kant el imperativo categórico manda obrar por deber de forma "
         "universal: actúa según una máxima que pueda ser ley universal y trata a la "
         "humanidad como fin y nunca solo como medio.", 8.0, 10.0),
        ("Aprobado", "El imperativo categórico de Kant dice que hay que actuar por "
         "deber siguiendo normas universales.", 4.0, 7.0),
        ("Suspenso", "Kant decía que hay que buscar el placer y la felicidad personal "
         "por encima de todo.", 0.0, 4.0),
    ],
))

# ── MATEMÁTICAS — cálculo (answer_checker) ────────────────────────────────────
# El grader determinista daba ALTA a una conclusión errónea por contener 'x = -3'
# como substring. El checker compara el RESULTADO final por equivalencia.
SUITES.append(dict(
    subject="Matemáticas", mode="numeric_math", solo="NO APTO", expected="x = -3",
    reference=ref("Matemáticas", "Resuelva la ecuación 2x + 6 = 0 e indique el resultado.",
        "Despejando, 2x = -6, por lo que x = -3.",
        [("x = -3", 0.6), ("despejar", 0.2), ("2x = -6", 0.2)]),
    cases=[
        ("Resultado correcto", "Paso 2x = -6 al otro lado y despejo: x = -3.", 8.0, 10.0),
        ("Resultado INCORRECTO con la palabra clave (humano: 0)",
         "Despejo 2x = -6 y me da x = -3... no, en realidad x = 3.", 0.0, 4.0),
        ("Equivalente en fracción (humano: 10)", "x = -6/2.", 8.0, 10.0),
    ],
))

# ── INGLÉS — redacción (grade_writing, LLM) ───────────────────────────────────
SUITES.append(dict(
    subject="Inglés", mode="writing", solo="NO APTO", rubric_subject="ingles",
    reference=ref("Inglés", "Write about the advantages of learning a foreign language.",
        "Learning a foreign language has many advantages...",
        [("advantages", 0.2), ("career", 0.2), ("travel", 0.2), ("cultures", 0.2),
         ("memory", 0.2)]),
    cases=[
        ("Notable (correcto y fluido)", "Learning a foreign language improves your "
         "career, lets you travel and meet people, helps you understand other cultures "
         "and boosts your memory.", 7.0, 10.0),
        ("Suspenso por GRAMÁTICA (mismas palabras, inglés roto)", "advantages career "
         "travel cultures memory me gusta language good for travel and cultures.",
         0.0, 4.5),
    ],
))

# ── LENGUA — comentario / redacción (grade_writing, LLM) ──────────────────────
SUITES.append(dict(
    subject="Lengua", mode="writing", solo="NO APTO", rubric_subject="lengua",
    reference=ref("Lengua", "Comente el tema y la intención del autor en el texto propuesto.",
        "El texto es un artículo de opinión cuyo tema es la dependencia de la "
        "tecnología...",
        [("artículo de opinión", 0.2), ("tema", 0.15), ("crítica", 0.2),
         ("persuadir", 0.2), ("argumentos", 0.15), ("ironía", 0.1)]),
    cases=[
        ("Notable", "Es un artículo de opinión cuyo tema es la dependencia tecnológica; "
         "el autor mantiene una actitud crítica y busca persuadir con argumentos y un "
         "tono irónico para que el lector reflexione sobre el uso del móvil.", 7.0, 10.0),
        ("Vacuo pero con palabras clave (un humano suspende)", "artículo de opinión "
         "tema crítica persuadir argumentos ironía bla bla bla relleno relleno.",
         0.0, 4.5),
    ],
))

# ── FÍSICA — enunciado teórico (grader) ───────────────────────────────────────
SUITES.append(dict(
    subject="Física", mode="concept", solo="PARCIAL",
    reference=ref("Física", "Enuncie la segunda ley de Newton.",
        "La segunda ley de Newton afirma que la fuerza neta que actúa sobre un "
        "cuerpo es igual al producto de su masa por la aceleración (F = m·a); la "
        "aceleración es proporcional a la fuerza y de su misma dirección.",
        [("fuerza", 0.3), ("masa", 0.25), ("aceleración", 0.25), ("proporcional", 0.2)]),
    cases=[
        ("Notable", "La fuerza neta sobre un cuerpo es igual a su masa por la "
         "aceleración, que es proporcional a la fuerza aplicada.", 8.0, 10.0),
        ("Aprobado", "La fuerza es la masa por la aceleración.", 4.0, 8.0),
        ("Suspenso", "Todo cuerpo permanece en reposo si no actúa ninguna energía "
         "sobre la temperatura.", 0.0, 4.0),
    ],
))


_MODE_LABEL = {
    "concept": "grader determinista",
    "numeric_math": "answer_checker (resultado)",
    "writing": "juez LLM (rúbrica)",
}


def grade_one(suite, grader, answer):
    """Enruta una respuesta a su corrector y devuelve (nota, detalle_corto)."""
    mode = suite["mode"]
    if mode == "concept":
        out = grader.grade(answer, suite["reference"])
        return out["score_over_10"], f"cr={out['concept_ratio']} sim={out['similarity_ratio']}"
    if mode == "numeric_math":
        out = grade_numeric(answer, suite["expected"], kind="math")
        return out["score_over_10"], out.get("detail", "")[:60]
    if mode == "writing":
        req = GradeWritingRequest(question=suite["reference"].question,
                                  student_answer=answer, subject=suite["rubric_subject"])
        out = grade_writing(req)
        return out["score_over_10"], (out.get("feedback", "")[:60])
    raise ValueError(mode)


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("AVISO: sin ANTHROPIC_API_KEY las preguntas de redacción (Inglés/Lengua) "
              "fallarán. Haz `set -a; . ./.env; set +a` antes de ejecutar.\n")

    grader = SemanticGrader()
    print("=" * 96)
    print("  EvAU 2026 — corrección HÍBRIDA (router por tipo de pregunta) vs profesor")
    print("=" * 96)

    rows = []
    g_ok = g_total = 0
    for suite in SUITES:
        print("\n" + "─" * 96)
        print(f"  {suite['subject'].upper():<12} [{_MODE_LABEL[suite['mode']]}]  ·  {suite['reference'].question}")
        print("─" * 96)
        ok = total = 0
        for desc, ans, lo, hi in suite["cases"]:
            try:
                score, detail = grade_one(suite, grader, ans)
            except Exception as exc:
                print(f"   [!] {desc}: ERROR {type(exc).__name__}: {exc}")
                total += 1
                continue
            inside = lo <= score <= hi
            ok += inside; total += 1
            print(f"   [{'✓' if inside else '✗'}] {desc}")
            print(f"        nota={score:<5} (humano {lo}-{hi})   {detail}")
        g_ok += ok; g_total += total
        rows.append((suite["subject"], suite["mode"], suite["solo"], ok, total))

    print("\n" + "=" * 96)
    print(f"  {'ASIGNATURA':<13}{'RUTA':<14}{'GRADER-SOLO':<13}{'HÍBRIDO':<10}")
    print("-" * 96)
    for subject, mode, solo, ok, total in rows:
        route = {"concept": "grader", "numeric_math": "checker", "writing": "LLM"}[mode]
        hibrido = f"{ok}/{total}" + ("  ✓" if ok == total else "")
        print(f"  {subject:<13}{route:<14}{solo:<13}{hibrido:<10}")
    print("-" * 96)
    print(f"  GLOBAL HÍBRIDO: {g_ok}/{g_total} respuestas en la banda del profesor "
          f"({round(100*g_ok/g_total)}%).")
    print("=" * 96)
    print("""
  LECTURA (como profesor):
    · El grader determinista ya bastaba para CONCEPTOS (Historia, Filosofía, Física
      teórica): interpretable y sin coste de API.
    · El router recupera lo que el grader NO podía juzgar:
        - Matemáticas → answer_checker distingue la conclusión errónea (x=3) de la
          correcta (x=-3) aunque ambas citen el símbolo, y acepta la fracción -6/2.
        - Inglés/Lengua → el juez LLM penaliza el inglés roto y el comentario vacuo
          aunque contengan todas las palabras clave.
    · No es "perfecto": es honesto. Cada nota la da el módulo que SÍ puede defender
      ese tipo de respuesta, y el sistema sigue siendo trazable (se ve qué ruta y por qué).
""")


if __name__ == "__main__":
    main()

"""
Experimento: ¿para qué asignaturas de EvAU/Bachillerato sirve el grader?

Pasamos por el SemanticGrader (determinista, sin API) preguntas de estilo EvAU
2026 de varias asignaturas, con respuestas de alumno de tres niveles
(notable/aprobado/suspenso). Para cada respuesta comparamos la nota del grader
con la banda que pondría un profesor. Al final, un veredicto por asignatura:

  APTO     → el grader ordena bien las respuestas (recuerdo de conceptos).
  PARCIAL  → funciona en lo memorístico pero se le escapan matices.
  NO APTO  → la asignatura exige evaluar redacción/razonamiento/cálculo, algo
             que un comparador de conceptos no puede juzgar.

Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/evau2026_todas_asignaturas.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader


def ref(subject, question, ideal, concepts):
    return ReferenceAnswer(
        question=question, subject=subject, education_level="Bachillerato",
        expected_answer_type="respuesta_corta", ideal_answer=ideal,
        key_concepts=[{"concept": c, "weight": w} for c, w in concepts],
    )


# Cada entrada: (referencia, [(desc, respuesta, banda_min, banda_max), ...], veredicto_humano)
SUITES = []

# ── HISTORIA DE ESPAÑA ───────────────────────────────────────────────────────
SUITES.append((
    ref("Historia", "Explique las características del reinado de los Reyes Católicos.",
        "Los Reyes Católicos, Isabel de Castilla y Fernando de Aragón, unieron "
        "dinásticamente Castilla y Aragón. Implantaron una monarquía autoritaria, "
        "conquistaron el reino nazarí de Granada en 1492, decretaron la expulsión "
        "de los judíos y crearon la Inquisición.",
        [("monarquía autoritaria", 0.25), ("Castilla", 0.15), ("Aragón", 0.15),
         ("Granada", 0.15), ("1492", 0.1), ("Inquisición", 0.1), ("judíos", 0.1)]),
    [("Notable", "Isabel de Castilla y Fernando de Aragón crearon una monarquía "
      "autoritaria, conquistaron Granada en 1492, expulsaron a los judíos e "
      "instauraron la Inquisición.", 8.0, 10.0),
     ("Aprobado", "Los Reyes Católicos unieron Castilla y Aragón y conquistaron "
      "Granada.", 4.5, 7.0),
     ("Suspenso", "Los Reyes Católicos perdieron la guerra contra Francia y "
      "abolieron la Inquisición.", 0.0, 4.0)],
    "APTO",
))

# ── FILOSOFÍA ────────────────────────────────────────────────────────────────
SUITES.append((
    ref("Filosofía", "Explique el concepto de imperativo categórico en Kant.",
        "El imperativo categórico es el principio moral kantiano que ordena actuar "
        "de forma universal e incondicional, por deber y no por interés. Una de sus "
        "formulaciones dice: obra de modo que la máxima de tu acción pueda "
        "convertirse en ley universal; otra exige tratar a la humanidad siempre como "
        "fin y nunca solo como medio.",
        [("imperativo categórico", 0.2), ("universal", 0.2), ("deber", 0.15),
         ("máxima", 0.15), ("ley universal", 0.15), ("fin", 0.1), ("medio", 0.05)]),
    [("Notable", "Para Kant el imperativo categórico manda obrar por deber de forma "
      "universal: actúa según una máxima que pueda ser ley universal y trata a la "
      "humanidad como fin y nunca solo como medio.", 8.0, 10.0),
     ("Aprobado", "El imperativo categórico de Kant dice que hay que actuar por "
      "deber siguiendo normas universales.", 4.0, 7.0),
     ("Suspenso", "Kant decía que hay que buscar el placer y la felicidad personal "
      "por encima de todo.", 0.0, 4.0)],
    "APTO",
))

# ── QUÍMICA ──────────────────────────────────────────────────────────────────
SUITES.append((
    ref("Química", "Defina enlace covalente y ponga un ejemplo.",
        "El enlace covalente se forma cuando dos átomos comparten uno o más pares "
        "de electrones, generalmente entre no metales. Un ejemplo es la molécula de "
        "agua, donde el oxígeno comparte electrones con dos hidrógenos.",
        [("comparten electrones", 0.35), ("no metales", 0.2),
         ("pares de electrones", 0.2), ("molécula", 0.15), ("agua", 0.1)]),
    [("Notable", "El enlace covalente se da cuando dos no metales comparten pares "
      "de electrones para formar una molécula, como en el agua.", 8.0, 10.0),
     ("Aprobado", "Es cuando los átomos comparten electrones.", 4.0, 7.5),
     ("Suspenso", "El enlace covalente es la atracción entre iones de carga "
      "opuesta que se transfieren electrones.", 0.0, 4.0)],
    "APTO",
))

# ── ECONOMÍA ─────────────────────────────────────────────────────────────────
SUITES.append((
    ref("Economía", "Defina inflación y explique una de sus causas.",
        "La inflación es el aumento generalizado y sostenido de los precios de los "
        "bienes y servicios, que reduce el poder adquisitivo del dinero. Una de sus "
        "causas es el exceso de demanda agregada respecto a la oferta (inflación de "
        "demanda).",
        [("aumento de los precios", 0.3), ("generalizado", 0.15), ("sostenido", 0.15),
         ("poder adquisitivo", 0.2), ("demanda", 0.2)]),
    [("Notable", "La inflación es el aumento generalizado y sostenido de los precios "
      "que reduce el poder adquisitivo; una causa es el exceso de demanda.", 8.0, 10.0),
     ("Aprobado", "La inflación es cuando suben los precios y el dinero vale menos.",
      4.0, 7.5),
     ("Suspenso", "La inflación es cuando bajan los precios y aumenta el paro en el "
      "país.", 0.0, 4.0)],
    "APTO",
))

# ── INGLÉS (composición / writing) ───────────────────────────────────────────
SUITES.append((
    ref("Inglés", "Write about the advantages of learning a foreign language.",
        "Learning a foreign language has many advantages. It improves your career "
        "opportunities, allows you to travel and meet new people, and helps you "
        "understand other cultures. Moreover, it boosts memory and brain skills.",
        [("advantages", 0.2), ("career", 0.2), ("travel", 0.2), ("cultures", 0.2),
         ("memory", 0.2)]),
    [("Notable (correcto y fluido)", "Learning a foreign language improves your "
      "career, lets you travel and meet people, helps you understand other cultures "
      "and boosts your memory.", 8.0, 10.0),
     ("Suspenso por GRAMÁTICA (mismas palabras, inglés roto)", "advantages career "
      "travel cultures memory me gusta language good for travel and cultures.",
      0.0, 4.0)],
    "NO APTO",  # el grader no ve gramática ni fluidez: la 2ª la aprobaría
))

# ── LENGUA CASTELLANA (comentario / redacción) ───────────────────────────────
SUITES.append((
    ref("Lengua", "Comente el tema y la intención del autor en el texto propuesto.",
        "El texto es un artículo de opinión cuyo tema es la dependencia de la "
        "tecnología. El autor adopta una actitud crítica y pretende persuadir al "
        "lector mediante argumentos y un tono irónico para que reflexione sobre el "
        "uso excesivo del móvil.",
        [("artículo de opinión", 0.2), ("tema", 0.15), ("crítica", 0.2),
         ("persuadir", 0.2), ("argumentos", 0.15), ("ironía", 0.1)]),
    [("Notable", "Es un artículo de opinión cuyo tema es la dependencia tecnológica; "
      "el autor mantiene una actitud crítica y busca persuadir con argumentos y un "
      "tono irónico.", 7.5, 10.0),
     ("Vacuo pero con palabras clave (un humano suspende)", "artículo de opinión "
      "tema crítica persuadir argumentos ironía bla bla bla relleno relleno.",
      0.0, 4.0)],
    "NO APTO",  # premia el vocabulario aunque no haya comentario real
))

# ── MATEMÁTICAS (cálculo) ────────────────────────────────────────────────────
SUITES.append((
    ref("Matemáticas", "Resuelva la ecuación 2x + 6 = 0 e indique el resultado.",
        "Despejando, 2x = -6, por lo que x = -3.",
        [("x = -3", 0.6), ("despejar", 0.2), ("2x = -6", 0.2)]),
    [("Resultado correcto", "Paso 2x = -6 al otro lado y despejo: x = -3.", 8.0, 10.0),
     ("Resultado INCORRECTO con la palabra clave (un humano: 0)",
      "Despejo 2x = -6 y me da x = -3... no, en realidad x = 3.", 0.0, 4.0)],
    "NO APTO",  # detecta 'x = -3' como substring aunque la conclusión sea errónea
))

# ── FÍSICA (concepto, parte memorística) ─────────────────────────────────────
SUITES.append((
    ref("Física", "Enuncie la segunda ley de Newton.",
        "La segunda ley de Newton afirma que la fuerza neta que actúa sobre un "
        "cuerpo es igual al producto de su masa por la aceleración (F = m·a); la "
        "aceleración es proporcional a la fuerza y de su misma dirección.",
        [("fuerza", 0.3), ("masa", 0.25), ("aceleración", 0.25),
         ("proporcional", 0.2)]),
    [("Notable", "La fuerza neta sobre un cuerpo es igual a su masa por la "
      "aceleración, que es proporcional a la fuerza aplicada.", 8.0, 10.0),
     ("Aprobado", "La fuerza es la masa por la aceleración.", 4.0, 8.0),
     ("Suspenso", "Todo cuerpo permanece en reposo si no actúa ninguna energía "
      "sobre la temperatura.", 0.0, 4.0)],
    "PARCIAL",  # bien en el enunciado teórico; no evaluaría un problema numérico
))


def main():
    grader = SemanticGrader()
    print("=" * 94)
    print("  EvAU/Bachillerato 2026 — ¿para qué asignaturas sirve el grader?")
    print("=" * 94)

    global_ok = global_total = 0
    verdicts = []

    for reference, answers, human_verdict in SUITES:
        print("\n" + "─" * 94)
        print(f"  {reference.subject.upper()}  ·  {reference.question}")
        print("─" * 94)
        ok = total = 0
        for desc, ans, lo, hi in answers:
            out = grader.grade(ans, reference)
            s = out["score_over_10"]
            inside = lo <= s <= hi
            ok += inside; total += 1
            global_ok += inside; global_total += 1
            print(f"   [{'✓' if inside else '✗'}] {desc}")
            print(f"        nota={s:<5} (humano {lo}-{hi})  cr={out['concept_ratio']} sim={out['similarity_ratio']}")
        verdicts.append((reference.subject, human_verdict, ok, total))

    print("\n" + "=" * 94)
    print("  VEREDICTO POR ASIGNATURA")
    print("=" * 94)
    for subject, verdict, ok, total in verdicts:
        print(f"   {subject:<14} {verdict:<8}  ({ok}/{total} respuestas en banda humana)")
    print("-" * 94)
    print(f"   GLOBAL: {global_ok}/{global_total} respuestas calificadas en la banda esperada por un profesor.")
    print("=" * 94)
    print("""
  LECTURA (como profesor):
    · APTO   → Historia, Filosofía, Química, Economía, Biología: preguntas de
               DEFINIR / EXPLICAR conceptos. El grader ordena bien las respuestas.
    · PARCIAL→ Física: vale para enunciados teóricos, NO para problemas numéricos.
    · NO APTO→ Inglés y Lengua (se evalúa redacción/gramática/comentario) y
               Matemáticas (cálculo): el grader premia las palabras clave aunque
               la respuesta sea incorrecta o esté mal escrita.
    → Conclusión: el corrector determinista es una buena ayuda para la parte
      MEMORÍSTICA/CONCEPTUAL de ciencias y humanidades; para redacción y cálculo
      hace falta el módulo de calibración/LLM (con criterio humano).
""")


if __name__ == "__main__":
    main()

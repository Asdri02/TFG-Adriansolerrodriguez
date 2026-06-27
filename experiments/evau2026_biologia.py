"""
Experimento: ¿corrige bien el grader preguntas REALES de la EvAU/PAU 2026?

Fuente: PRUEBA DE ACCESO A LA UNIVERSIDAD — PAU 2026, 311 BIOLOGÍA (ejemplo
oficial de examen, Universidad de Murcia / UPCT). PDF en
experiments/PAU2026_311_Biologia_Murcia.pdf.

El examen oficial no publica la respuesta correcta, así que las respuestas
modelo y las rúbricas (key_concepts + pesos) las hemos construido a mano a
partir del enunciado, con biología correcta a nivel de 2º de Bachillerato.

Para cada pregunta probamos varias respuestas de alumno de distinta calidad y
comparamos la nota del grader (0-10) con la BANDA esperada que asignaría un
corrector humano. No se usa la API de Claude: se llama directamente a
SemanticGrader, así que esto corre sin ANTHROPIC_API_KEY.

Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/evau2026_biologia.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader


def ref(question, ideal, concepts):
    return ReferenceAnswer(
        question=question,
        subject="Biología",
        education_level="Bachillerato",
        expected_answer_type="respuesta_corta",
        ideal_answer=ideal,
        key_concepts=[{"concept": c, "weight": w} for c, w in concepts],
    )


# ── Pregunta 4.1.A — Fotosíntesis y polímeros ────────────────────────────────
P_FOTOSINTESIS = ref(
    "Explique en qué consiste la fotosíntesis. Nombre e indique la función de dos "
    "polímeros que las células vegetales puedan formar a partir de la biomolécula "
    "que se genera en la fotosíntesis e indique el tipo de enlace implicado.",
    ideal=(
        "La fotosíntesis es el proceso por el que los organismos autótrofos "
        "transforman la energía luminosa en energía química, sintetizando materia "
        "orgánica (glucosa) a partir de dióxido de carbono y agua y liberando "
        "oxígeno. A partir de la glucosa las células vegetales forman almidón, "
        "polímero de reserva energética, y celulosa, polímero estructural de la "
        "pared celular; ambos se unen mediante enlaces glucosídicos."
    ),
    concepts=[
        ("energía luminosa", 0.15),
        ("energía química", 0.15),
        ("glucosa", 0.15),
        ("dióxido de carbono", 0.10),
        ("agua", 0.05),
        ("oxígeno", 0.10),
        ("almidón", 0.10),
        ("celulosa", 0.10),
        ("enlace glucosídico", 0.10),
    ],
)

# ── Pregunta 5.1.C1 — PCR ────────────────────────────────────────────────────
P_PCR = ref(
    "En relación con la PCR: explique para qué se utiliza y qué procesos tienen "
    "lugar en cada ciclo.",
    ideal=(
        "La PCR (reacción en cadena de la polimerasa) se utiliza para amplificar "
        "in vitro un fragmento de ADN, obteniendo millones de copias. Cada ciclo "
        "consta de tres fases: desnaturalización, en la que el calor separa las dos "
        "hebras; hibridación o annealing, en la que los cebadores se unen a las "
        "hebras molde; y extensión, en la que la ADN polimerasa sintetiza la hebra "
        "complementaria."
    ),
    concepts=[
        ("amplificar", 0.20),
        ("ADN", 0.15),
        ("copias", 0.10),
        ("desnaturalización", 0.15),
        ("hibridación", 0.15),
        ("extensión", 0.15),
        ("polimerasa", 0.10),
    ],
)

# ── Pregunta 2.A — Genética (razonamiento dominante/recesivo) ────────────────
P_GENETICA = ref(
    "Ernesto y Elena tienen ambos una enfermedad autosómica (alelos M y m) y "
    "tienen un hijo sano. Indique, razonando, si es dominante o recesiva y los "
    "genotipos de Ernesto y Elena.",
    ideal=(
        "La enfermedad es dominante. Como ambos progenitores están afectados pero "
        "tienen un hijo sano, no pueden ser homocigotos recesivos; deben ser "
        "heterocigotos: Ernesto Mm y Elena Mm. Del cruce Mm x Mm puede salir un "
        "hijo sano de genotipo mm."
    ),
    concepts=[
        ("dominante", 0.40),
        ("heterocigotos", 0.30),
        ("Mm", 0.30),
    ],
)


# (pregunta, descripción, respuesta_alumno, banda_min, banda_max esperadas)
CASES = [
    # ---- Fotosíntesis ----
    (P_FOTOSINTESIS, "Respuesta de sobresaliente (modelo)",
     "La fotosíntesis transforma la energía luminosa en energía química y produce "
     "glucosa a partir de dióxido de carbono y agua, liberando oxígeno. Con la "
     "glucosa la célula vegetal fabrica almidón como reserva y celulosa para la "
     "pared, unidos por enlaces glucosídicos.",
     8.0, 10.0),

    (P_FOTOSINTESIS, "Respuesta de aprobado justo (olvida los polímeros)",
     "La fotosíntesis usa la luz para crear energía química y glucosa a partir de "
     "dióxido de carbono y agua, y desprende oxígeno.",
     5.0, 7.5),

    (P_FOTOSINTESIS, "Respuesta incorrecta (confunde con respiración)",
     "La fotosíntesis es cuando la célula consume oxígeno y glucosa para obtener "
     "energía en la mitocondria, liberando dióxido de carbono.",
     0.0, 4.5),

    (P_FOTOSINTESIS, "ADVERSARIA: lista de palabras clave sin coherencia",
     "energía luminosa energía química glucosa dióxido de carbono agua oxígeno "
     "almidón celulosa enlace glucosídico",
     0.0, 5.0),  # un humano daría poco; esperamos que el grader la SOBREVALORE

    # ---- PCR ----
    (P_PCR, "Respuesta de sobresaliente (modelo)",
     "La PCR sirve para amplificar un fragmento de ADN y obtener millones de "
     "copias. En cada ciclo hay desnaturalización para separar las hebras, "
     "hibridación de los cebadores y extensión por la ADN polimerasa.",
     8.0, 10.0),

    (P_PCR, "Respuesta de aprobado (sabe para qué sirve, falla las fases)",
     "La PCR se usa para amplificar el ADN y hacer muchas copias de un fragmento, "
     "pero no recuerdo bien los pasos de cada ciclo.",
     4.0, 7.0),

    (P_PCR, "Respuesta en blanco / irrelevante",
     "No me dio tiempo a estudiar este tema.",
     0.0, 2.0),

    # ---- Genética (razonamiento) ----
    (P_GENETICA, "Respuesta correcta y razonada",
     "Es dominante, porque dos padres enfermos tienen un hijo sano, así que son "
     "heterocigotos Mm y Mm; el hijo sano es mm.",
     8.0, 10.0),

    (P_GENETICA, "Respuesta con razonamiento ERRÓNEO (dice recesiva)",
     "La enfermedad es recesiva y los dos padres son homocigotos recesivos mm y mm.",
     0.0, 4.0),

    (P_GENETICA, "ADVERSARIA: términos correctos, razonamiento ausente",
     "dominante heterocigotos Mm",
     0.0, 6.0),  # un humano exige el razonamiento del cruce; el grader no lo ve
]


def main():
    grader = SemanticGrader()
    print("=" * 92)
    print("  EvAU/PAU 2026 · BIOLOGÍA (Murcia) — ¿corrige bien el grader?")
    print("=" * 92)

    current_q = None
    aciertos = 0
    sobrevalora_adversaria = []

    for reference, desc, answer, lo, hi in CASES:
        if reference.question != current_q:
            current_q = reference.question
            print("\n" + "-" * 92)
            print("PREGUNTA:", reference.question[:88])
            print("-" * 92)

        out = grader.grade(answer, reference)
        score = out["score_over_10"]
        dentro = lo <= score <= hi
        marca = "✓" if dentro else "✗"
        if dentro:
            aciertos += 1
        if "ADVERSARIA" in desc and score > 5.0:
            sobrevalora_adversaria.append((desc, score))

        print(f"  [{marca}] {desc}")
        print(f"        nota={score:<5}  (banda humana esperada {lo}-{hi})"
              f"   cr={out['concept_ratio']}  sim={out['similarity_ratio']}  lp={out['length_penalty']}")
        det = ", ".join(out["detected_concepts"]) or "—"
        mis = ", ".join(out["missing_concepts"]) or "—"
        print(f"        detectados: {det}")
        print(f"        faltan:     {mis}")

    print("\n" + "=" * 92)
    print(f"  RESUMEN: {aciertos}/{len(CASES)} respuestas caen en la banda esperada por un humano.")
    if sobrevalora_adversaria:
        print("  Limitación confirmada — sobrevalora respuestas adversarias (keyword-stuffing):")
        for d, s in sobrevalora_adversaria:
            print(f"    · {d} → {s}/10")
    print("=" * 92)


if __name__ == "__main__":
    main()

"""
gold_dataset.py — Conjunto de respuestas con NOTA HUMANA de referencia.

ADVERTENCIA DE HONESTIDAD (para la memoria del TFG): estas notas humanas no
provienen de exámenes corregidos por un tribunal real. Son notas de referencia
asignadas a mano por el autor emulando el criterio de un profesor de
Bachillerato/universidad, a partir de cada rúbrica. Sirven para medir si el
sistema ORDENA y aproxima las notas como lo haría un humano; no son un dataset
clínico. Para una validación definitiva habría que recoger correcciones reales
de varios profesores y medir además la concordancia entre ellos.

Estructura: por cada pregunta, una referencia (pregunta + ideal + conceptos) y
una lista de (respuesta_alumno, nota_humana 0-10) repartida por toda la escala.

Vive en `src/ai/` (no en `experiments/`) para que tanto los experimentos como la
API web (`/api/correlation`) puedan importarlo sin acoplarse entre sí.
"""

from __future__ import annotations

from ai.models import ReferenceAnswer


def _ref(subject, question, ideal, concepts):
    return ReferenceAnswer(
        question=question, subject=subject, education_level="Bachillerato",
        expected_answer_type="respuesta_corta", ideal_answer=ideal,
        key_concepts=[{"concept": c, "weight": w} for c, w in concepts],
    )


# ── 1. Mitocondria (Biología) ────────────────────────────────────────────────
_MITOCONDRIA = _ref(
    "Biología", "¿Cuál es la función principal de la mitocondria?",
    "La mitocondria es el orgánulo encargado de la respiración celular, donde se "
    "produce ATP mediante la fosforilación oxidativa.",
    [("respiración celular", 0.4), ("ATP", 0.3), ("fosforilación oxidativa", 0.3)])

# ── 2. Fotosíntesis (Biología) ───────────────────────────────────────────────
_FOTOSINTESIS = _ref(
    "Biología", "¿Qué es la fotosíntesis y qué produce?",
    "La fotosíntesis transforma la energía luminosa en energía química, "
    "produciendo glucosa a partir de dióxido de carbono y agua y liberando oxígeno.",
    [("energía luminosa", 0.2), ("glucosa", 0.25), ("dióxido de carbono", 0.2),
     ("oxígeno", 0.2), ("agua", 0.15)])

# ── 3. ADN (Biología) ────────────────────────────────────────────────────────
_ADN = _ref(
    "Biología", "¿Qué es el ADN y cuál es su función?",
    "El ADN es la molécula que almacena la información genética en forma de una "
    "doble hélice de nucleótidos, y dirige la síntesis de proteínas.",
    [("información genética", 0.35), ("doble hélice", 0.25),
     ("nucleótidos", 0.2), ("proteínas", 0.2)])

# ── 4. Variable (Informática) ────────────────────────────────────────────────
_VARIABLE = _ref(
    "Informática", "¿Qué es una variable en programación?",
    "Una variable es una zona de memoria identificada por un nombre que guarda "
    "un valor de un tipo determinado.",
    [("memoria", 0.3), ("nombre", 0.25), ("valor", 0.25), ("tipo", 0.2)])

# ── 5. Clave primaria (Informática) ──────────────────────────────────────────
_CLAVE = _ref(
    "Informática", "¿Qué es una clave primaria en una base de datos relacional?",
    "Una clave primaria es un campo o conjunto de campos que identifica de forma "
    "única cada fila de una tabla y cuyo valor no puede ser nulo.",
    [("única", 0.3), ("tabla", 0.2), ("fila", 0.25), ("no nulo", 0.25)])

# ── 6. Complejidad temporal (Informática) ────────────────────────────────────
_COMPLEJIDAD = _ref(
    "Informática", "¿Qué mide la complejidad temporal de un algoritmo?",
    "La complejidad temporal mide cómo crece el número de operaciones de un "
    "algoritmo en función del tamaño de la entrada, normalmente con notación "
    "asintótica O grande para el peor caso.",
    [("operaciones", 0.3), ("tamaño de la entrada", 0.3),
     ("notación asintótica", 0.2), ("peor caso", 0.2)])


# (respuesta, nota_humana 0-10) — repartidas por toda la escala.
GOLD = [
    (_MITOCONDRIA, [
        ("La mitocondria es el orgánulo de la respiración celular donde se produce "
         "ATP mediante la fosforilación oxidativa.", 10.0),
        ("La mitocondria produce ATP en la respiración celular.", 7.5),
        ("Es el orgánulo que da energía a la célula mediante la respiración.", 5.5),
        ("La mitocondria interviene en procesos de la célula.", 2.5),
        ("La mitocondria almacena la información genética de la célula.", 0.5),
    ]),
    (_FOTOSINTESIS, [
        ("La fotosíntesis transforma la energía luminosa en química y produce "
         "glucosa a partir de dióxido de carbono y agua, liberando oxígeno.", 10.0),
        ("La fotosíntesis usa la luz para crear glucosa y libera oxígeno a partir "
         "de dióxido de carbono y agua.", 8.5),
        ("La fotosíntesis produce glucosa y oxígeno usando la luz del sol.", 6.0),
        ("La fotosíntesis es un proceso de las plantas con la luz.", 3.0),
        ("La fotosíntesis consume oxígeno y glucosa para dar energía.", 1.0),
    ]),
    (_ADN, [
        ("El ADN almacena la información genética en una doble hélice de "
         "nucleótidos y dirige la síntesis de proteínas.", 10.0),
        ("El ADN guarda la información genética en forma de doble hélice de "
         "nucleótidos.", 7.5),
        ("El ADN contiene la información genética de los seres vivos.", 5.0),
        ("El ADN es una molécula muy importante del cuerpo.", 2.0),
        ("El ADN es el orgánulo que produce energía en la célula.", 0.5),
    ]),
    (_VARIABLE, [
        ("Una variable es una zona de memoria con un nombre que guarda un valor de "
         "un tipo determinado.", 10.0),
        ("Una variable es un espacio en memoria con un nombre donde se guarda un "
         "valor.", 7.5),
        ("Una variable guarda un valor en el programa.", 5.0),
        ("Una variable sirve para programar cosas.", 2.0),
        ("Una variable es una función que repite instrucciones.", 0.5),
    ]),
    (_CLAVE, [
        ("La clave primaria identifica de forma única cada fila de una tabla y su "
         "valor no puede ser nulo.", 10.0),
        ("La clave primaria es un campo que identifica de forma única cada fila de "
         "una tabla.", 7.5),
        ("La clave primaria identifica los registros de una tabla.", 5.5),
        ("La clave primaria es algo importante de las bases de datos.", 1.5),
        ("La clave primaria puede repetirse y tener valor nulo en la tabla.", 2.0),
    ]),
    (_COMPLEJIDAD, [
        ("La complejidad temporal mide cómo crece el número de operaciones en "
         "función del tamaño de la entrada, con notación asintótica O grande para "
         "el peor caso.", 10.0),
        ("Mide cómo crece el número de operaciones según el tamaño de la entrada "
         "usando la notación O grande.", 8.0),
        ("Mide cuántas operaciones hace un algoritmo según la entrada.", 6.0),
        ("Mide lo que tarda un algoritmo en ejecutarse.", 3.5),
        ("Es la cantidad de memoria que usa un algoritmo.", 1.0),
    ]),
]

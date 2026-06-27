"""
validate.py — 40 test cases for the semantic grading system.

Run from the src/ directory:
    python validate.py

Or from the project root:
    python src/validate.py

Prints each case with its score, expected range, and PASS/FAIL.
Termina con resultados globales y desglose por tema y asignatura.
"""

from collections import defaultdict

from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader


# ── Helper ────────────────────────────────────────────────────────────────────

def _ref(
    question: str,
    ideal_answer: str,
    key_concepts: list,
    subject: str = "Biología",
    education_level: str = "Bachillerato",
) -> ReferenceAnswer:
    return ReferenceAnswer(
        question=question,
        subject=subject,
        education_level=education_level,
        expected_answer_type="respuesta_corta",
        ideal_answer=ideal_answer,
        key_concepts=key_concepts,
        confidence=0.95,
    )


# ── Shared references ─────────────────────────────────────────────────────────

_REF_MITOCONDRIA = _ref(
    question="¿Cuál es la función principal de la mitocondria?",
    ideal_answer=(
        "La mitocondria es el orgánulo celular encargado de producir energía "
        "en forma de ATP mediante la respiración celular."
    ),
    key_concepts=[
        {"concept": "orgánulo",          "weight": 0.15},
        {"concept": "energía",           "weight": 0.25},
        {"concept": "ATP",               "weight": 0.35},
        {"concept": "respiración celular","weight": 0.25},
    ],
)

_REF_FOTOSINTESIS = _ref(
    question="¿Qué es la fotosíntesis y dónde ocurre?",
    ideal_answer=(
        "La fotosíntesis es el proceso mediante el cual las plantas convierten "
        "la energía lumínica en glucosa y oxígeno, usando dióxido de carbono y "
        "agua. Ocurre en los cloroplastos."
    ),
    key_concepts=[
        {"concept": "energía lumínica",    "weight": 0.20},
        {"concept": "glucosa",             "weight": 0.25},
        {"concept": "oxígeno",             "weight": 0.15},
        {"concept": "dióxido de carbono",  "weight": 0.15},
        {"concept": "cloroplasto",         "weight": 0.25},
    ],
)

_REF_ADN = _ref(
    question="¿Qué es el ADN y cuál es su función?",
    ideal_answer=(
        "El ADN o ácido desoxirribonucleico es la molécula portadora de la "
        "información genética de los seres vivos. Tiene estructura de doble "
        "hélice formada por nucleótidos y se localiza principalmente en el "
        "núcleo celular."
    ),
    key_concepts=[
        {"concept": "información genética", "weight": 0.35},
        {"concept": "doble hélice",         "weight": 0.25},
        {"concept": "nucleótido",           "weight": 0.20},
        {"concept": "núcleo",               "weight": 0.20},
    ],
)

_REF_CELULA_VEGETAL = _ref(
    question="¿Qué diferencias estructurales hay entre una célula vegetal y una célula animal?",
    ideal_answer=(
        "Las células vegetales tienen pared celular de celulosa, cloroplastos "
        "que realizan la fotosíntesis, y una vacuola central de gran tamaño. "
        "Las células animales carecen de pared celular y cloroplastos, tienen "
        "vacuolas pequeñas y poseen centríolos que participan en la división celular."
    ),
    key_concepts=[
        {"concept": "pared celular",   "weight": 0.25},
        {"concept": "cloroplasto",     "weight": 0.25},
        {"concept": "vacuola",         "weight": 0.20},
        {"concept": "centríolo",       "weight": 0.15},
        {"concept": "celulosa",        "weight": 0.15},
    ],
)

# ── Referencias de Informática (universitario) ───────────────────────────────
#
# El synonym_map del grader está cargado con vocabulario de biología
# (producir, energía, célula, ATP…). Para Informática los conceptos clave se
# eligen entre términos que el alumno va a escribir literalmente o que el
# matcher fuzzy (SequenceMatcher ≥ 0.80) puede asimilar. Evitar tokens
# demasiado cortos o ambiguos ("dato", "valor" solo) porque generan
# falsos positivos al estar en cualquier respuesta.

_REF_VARIABLE = _ref(
    question="¿Qué es una variable en programación y qué características tiene?",
    ideal_answer=(
        "Una variable es un espacio en memoria identificado con un nombre que "
        "almacena un valor de un tipo determinado y cuyo contenido puede "
        "modificarse durante la ejecución del programa."
    ),
    key_concepts=[
        {"concept": "memoria", "weight": 0.30},
        {"concept": "nombre",  "weight": 0.20},
        {"concept": "valor",   "weight": 0.25},
        {"concept": "tipo",    "weight": 0.25},
    ],
    subject="Informática",
    education_level="Universitario",
)

_REF_COMPLEJIDAD = _ref(
    question="¿Qué es la complejidad temporal de un algoritmo?",
    ideal_answer=(
        "La complejidad temporal mide el tiempo de ejecución de un algoritmo "
        "en función del tamaño de la entrada. Se expresa habitualmente con la "
        "notación Big-O para describir su comportamiento asintótico en el peor caso."
    ),
    key_concepts=[
        {"concept": "tiempo",      "weight": 0.25},
        {"concept": "entrada",     "weight": 0.20},
        {"concept": "asintótico",  "weight": 0.30},
        {"concept": "peor caso",   "weight": 0.25},
    ],
    subject="Informática",
    education_level="Universitario",
)

_REF_HTTP = _ref(
    question="¿Qué es el protocolo HTTP y para qué se utiliza?",
    ideal_answer=(
        "HTTP es un protocolo de la capa de aplicación que define cómo se "
        "comunican clientes y servidores web mediante peticiones y respuestas. "
        "Se utiliza para transferir recursos hipertexto en la World Wide Web."
    ),
    key_concepts=[
        {"concept": "protocolo", "weight": 0.20},
        {"concept": "cliente",   "weight": 0.25},
        {"concept": "servidor",  "weight": 0.25},
        {"concept": "petición",  "weight": 0.30},
    ],
    subject="Informática",
    education_level="Universitario",
)

_REF_CLAVE_PRIMARIA = _ref(
    question="¿Qué es una clave primaria en una base de datos relacional?",
    ideal_answer=(
        "Una clave primaria es un campo o conjunto de campos que identifica "
        "de forma única cada fila de una tabla. Debe ser un valor único, no "
        "nulo y estable a lo largo del tiempo."
    ),
    key_concepts=[
        {"concept": "única",   "weight": 0.30},
        {"concept": "tabla",   "weight": 0.20},
        {"concept": "fila",    "weight": 0.25},
        # La restricción es NOT NULL: el concepto correcto es "no nulo", no "nulo"
        # a secas. Así el detector de polaridad distingue "no puede ser nulo"
        # (correcto) de "puede ser nulo" (incorrecto), en vez de premiar a ambos.
        {"concept": "no nulo", "weight": 0.25},
    ],
    subject="Informática",
    education_level="Universitario",
)


# ── Test cases ────────────────────────────────────────────────────────────────
#
# nota_min / nota_max are the inclusive bounds [0, 10] that the grader's
# score_over_10 must fall within for the case to PASS.
#
# Rationale for each range is in the inline comment.

TEST_CASES = [

    # ── Mitocondria (3 cases) ─────────────────────────────────────────────────

    {
        "id": 1,
        "topic": "Mitocondria",
        "desc": "Respuesta completa (todos los conceptos)",
        "reference": _REF_MITOCONDRIA,
        "student_answer": (
            "La mitocondria es el orgánulo celular responsable de producir "
            "energía en forma de ATP mediante la respiración celular aeróbica."
        ),
        # orgánulo ✓  energía ✓  ATP ✓  respiración celular ✓ → concept_ratio=1.0
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 2,
        "topic": "Mitocondria",
        "desc": "Respuesta parcial (sin ATP, con los demás conceptos)",
        "reference": _REF_MITOCONDRIA,
        "student_answer": (
            "La mitocondria es el orgánulo donde se produce energía "
            "mediante la respiración celular."
        ),
        # orgánulo ✓  energía ✓  ATP ✗  respiración celular ✓ → concept_ratio=0.65
        # min_floor=0.6 activo  →  score ~6-7
        "nota_min": 5.0,
        "nota_max": 8.5,
    },
    {
        "id": 3,
        "topic": "Mitocondria",
        "desc": "Respuesta incorrecta (describe el núcleo)",
        "reference": _REF_MITOCONDRIA,
        "student_answer": (
            "La mitocondria controla la división celular y almacena "
            "el material genético de la célula."
        ),
        # ningún concepto detectado → concept_ratio=0.0  →  score ~0
        "nota_min": 0.0,
        "nota_max": 2.0,
    },

    # ── Fotosíntesis (3 cases) ────────────────────────────────────────────────

    {
        "id": 4,
        "topic": "Fotosíntesis",
        "desc": "Respuesta completa (todos los conceptos)",
        "reference": _REF_FOTOSINTESIS,
        "student_answer": (
            "La fotosíntesis transforma energía lumínica en glucosa, usando "
            "dióxido de carbono y agua. Ocurre en los cloroplastos y libera "
            "oxígeno como subproducto."
        ),
        # todos los conceptos detectados → concept_ratio=1.0  →  score ~9-10
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 5,
        "topic": "Fotosíntesis",
        "desc": "Respuesta parcial (glucosa y oxígeno, sin cloroplasto ni CO₂)",
        "reference": _REF_FOTOSINTESIS,
        "student_answer": (
            "La fotosíntesis utiliza luz solar para producir glucosa y "
            "oxígeno en las células vegetales."
        ),
        # glucosa ✓  oxígeno ✓  energía lumínica ✗  CO₂ ✗  cloroplasto ✗
        # concept_ratio=0.40, length_factor<1.0  →  score ~2-4
        "nota_min": 2.0,
        "nota_max": 5.5,
    },
    {
        "id": 6,
        "topic": "Fotosíntesis",
        "desc": "Respuesta muy pobre (solo idea general, sin términos técnicos)",
        "reference": _REF_FOTOSINTESIS,
        "student_answer": (
            "La fotosíntesis es un proceso que realizan las plantas con la luz."
        ),
        # ningún concepto técnico → concept_ratio≈0  →  score ~0-1
        "nota_min": 0.0,
        "nota_max": 3.0,
    },

    # ── ADN (4 cases) ─────────────────────────────────────────────────────────

    {
        "id": 7,
        "topic": "ADN",
        "desc": "Respuesta completa (todos los conceptos)",
        "reference": _REF_ADN,
        "student_answer": (
            "El ADN contiene la información genética. Su estructura es una "
            "doble hélice formada por nucleótidos, y se localiza en el núcleo "
            "de la célula eucariota."
        ),
        # información genética ✓  doble hélice ✓  nucleótido ✓  núcleo ✓
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 8,
        "topic": "ADN",
        "desc": "Respuesta parcial (solo menciona información genética)",
        "reference": _REF_ADN,
        "student_answer": "El ADN contiene la información genética del organismo.",
        # información genética ✓  resto ✗ → concept_ratio=0.35, respuesta corta
        # length_factor=0.8  →  score ~2-3
        "nota_min": 2.0,
        "nota_max": 5.0,
    },
    {
        "id": 9,
        "topic": "ADN",
        "desc": "Respuesta parcial (estructura sin función: sin información genética)",
        "reference": _REF_ADN,
        "student_answer": (
            "El ADN tiene una doble hélice de nucleótidos que se localiza "
            "en el núcleo celular."
        ),
        # doble hélice ✓  nucleótido ✓  núcleo ✓  información genética ✗
        # concept_ratio=0.65 → min_floor=0.6 activo  →  score ~6
        "nota_min": 5.0,
        "nota_max": 8.0,
    },
    {
        "id": 10,
        "topic": "ADN",
        "desc": "Respuesta trivial (sin conceptos concretos)",
        "reference": _REF_ADN,
        "student_answer": "El ADN es una molécula muy importante para las células.",
        # ningún concepto técnico → concept_ratio=0  →  score ~0
        "nota_min": 0.0,
        "nota_max": 2.0,
    },

    # ── Sinónimos: ejercitan la bidireccionalidad de expand_with_synonyms ────

    {
        "id": 11,
        "topic": "Mitocondria",
        "desc": "Vocabulario alternativo: 'obtiene' en respuesta correcta",
        "reference": _REF_MITOCONDRIA,
        "student_answer": (
            "La mitocondria es el orgánulo donde se obtiene energía en forma "
            "de ATP gracias a la respiración celular."
        ),
        # orgánulo ✓  energía ✓  ATP ✓  respiración celular ✓
        # "obtiene" pertenece al grupo "producir" → expansión bidireccional
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 12,
        "topic": "Fotosíntesis",
        "desc": "Vocabulario alternativo: 'fabricar' en respuesta correcta",
        "reference": _REF_FOTOSINTESIS,
        "student_answer": (
            "Las plantas fabrican glucosa y oxígeno a partir de dióxido de "
            "carbono y agua usando energía lumínica en los cloroplastos."
        ),
        # energía lumínica ✓  glucosa ✓  oxígeno ✓  CO₂ ✓  cloroplasto ✓
        # "fabricar" → grupo "producir"; el resto está explícito
        "nota_min": 8.0,
        "nota_max": 10.0,
    },

    # ── Errores conceptuales: vocabulario reutilizado pero relación incorrecta ─

    {
        "id": 13,
        "topic": "Mitocondria",
        "desc": "Error conceptual: confunde mitocondria con núcleo",
        "reference": _REF_MITOCONDRIA,
        "student_answer": (
            "La mitocondria es la parte de la célula donde se guarda la "
            "información genética y el ADN."
        ),
        # "mitocondria" presente pero ningún concepto de la rúbrica cubierto
        # (orgánulo, energía, ATP, respiración celular) → concept_ratio≈0
        "nota_min": 0.0,
        "nota_max": 2.5,
    },
    {
        "id": 14,
        "topic": "Fotosíntesis",
        "desc": "Error conceptual: describe respiración celular en lugar de fotosíntesis",
        "reference": _REF_FOTOSINTESIS,
        "student_answer": (
            "La fotosíntesis es el proceso por el que las células consumen "
            "oxígeno y glucosa para liberar energía."
        ),
        # glucosa ✓ y oxígeno ✓ aparecen pero la dirección del proceso es la
        # opuesta; faltan energía lumínica, CO₂, cloroplasto → concept_ratio bajo
        "nota_min": 0.0,
        "nota_max": 3.0,
        # FAIL esperado: el sistema no detecta que la dirección del proceso es
        # la inversa. Es la limitación que motiva la línea futura de
        # "anti-patterns" descrita en CLAUDE.md.
        "expected_to_fail": True,
    },

    # ── Borderline de longitud ──────────────────────────────────────────────

    {
        "id": 15,
        "topic": "Mitocondria",
        "desc": "Respuesta correcta pero brevísima (length_penalty vs min_floor)",
        "reference": _REF_MITOCONDRIA,
        "student_answer": "Orgánulo que produce ATP por respiración celular.",
        # orgánulo ✓  ATP ✓  respiración celular ✓  energía ✗ (implícita en ATP)
        # concept_ratio=0.75  →  min_floor=0.6 activo
        # length_penalty alto por brevedad pero el suelo lo sostiene
        "nota_min": 4.5,
        "nota_max": 8.0,
    },
    {
        "id": 16,
        "topic": "ADN",
        "desc": "Respuesta larga con conceptos diluidos (texto de relleno)",
        "reference": _REF_ADN,
        "student_answer": (
            "El ADN es una de las moléculas más fascinantes de la biología. "
            "Está presente en todos los seres vivos conocidos hasta la fecha "
            "y ha sido objeto de muchísimos estudios desde su descubrimiento. "
            "Tiene una forma característica que se ha popularizado mucho en "
            "libros, películas y documentales."
        ),
        # ningún concepto técnico de la rúbrica (información genética, doble
        # hélice, nucleótido, núcleo). Texto largo pero vacío de contenido.
        "nota_min": 0.0,
        "nota_max": 2.5,
    },

    # ── Célula vegetal vs. animal (6 casos) ─────────────────────────────────

    {
        "id": 17,
        "topic": "Célula vegetal/animal",
        "desc": "Respuesta completa (ambos tipos celulares contrastados)",
        "reference": _REF_CELULA_VEGETAL,
        "student_answer": (
            "Las células vegetales tienen pared celular de celulosa, "
            "cloroplastos para la fotosíntesis y una gran vacuola central. "
            "Las animales no tienen pared celular ni cloroplastos, sus "
            "vacuolas son pequeñas y tienen centríolos."
        ),
        # pared celular ✓  cloroplasto ✓  vacuola ✓  centríolo ✓  celulosa ✓
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 18,
        "topic": "Célula vegetal/animal",
        "desc": "Correcta enfocada solo en la célula vegetal",
        "reference": _REF_CELULA_VEGETAL,
        "student_answer": (
            "La célula vegetal se diferencia por tener pared celular formada "
            "por celulosa, cloroplastos y vacuolas grandes."
        ),
        # pared celular ✓  celulosa ✓  cloroplasto ✓  vacuola ✓  centríolo ✗
        # concept_ratio=0.85; respuesta corta → length_penalty puede activarse
        "nota_min": 5.5,
        "nota_max": 8.5,
    },
    {
        "id": 19,
        "topic": "Célula vegetal/animal",
        "desc": "Respuesta parcial (solo pared celular)",
        "reference": _REF_CELULA_VEGETAL,
        "student_answer": "La célula vegetal tiene pared celular y la animal no.",
        # pared celular ✓  resto ✗ → concept_ratio=0.25; muy breve
        "nota_min": 2.0,
        "nota_max": 5.0,
    },
    {
        "id": 20,
        "topic": "Célula vegetal/animal",
        "desc": "Vocabulario adyacente sin precisión técnica",
        "reference": _REF_CELULA_VEGETAL,
        "student_answer": (
            "Las células de las plantas son rígidas y tienen partes verdes "
            "para hacer la fotosíntesis."
        ),
        # ningún término de la rúbrica aparece literalmente: "verdes" no
        # matchea "cloroplasto", "rígidas" no matchea "pared celular"
        "nota_min": 1.5,
        "nota_max": 4.5,
    },
    {
        "id": 21,
        "topic": "Célula vegetal/animal",
        "desc": "Error conceptual: invierte qué célula tiene cada estructura",
        "reference": _REF_CELULA_VEGETAL,
        "student_answer": (
            "Las células animales tienen pared celular y cloroplastos, "
            "mientras que las vegetales no."
        ),
        # los conceptos pared celular y cloroplasto aparecen pero atribuidos
        # al tipo celular incorrecto. El sistema no detecta la inversión.
        "nota_min": 4.0,
        "nota_max": 5.0,
        # PASS expected by collateral penalization (incompleteness + length),
        # NOT because the system detects the role inversion. A long, complete
        # but inverted answer would expose the same limitation as case 14.
    },
    {
        "id": 22,
        "topic": "Célula vegetal/animal",
        "desc": "Respuesta trivial (sin contenido técnico)",
        "reference": _REF_CELULA_VEGETAL,
        "student_answer": "Hay diferencias entre las células vegetales y las animales.",
        # ningún concepto técnico → concept_ratio≈0
        "nota_min": 0.0,
        "nota_max": 2.0,
    },

    # ── Variable / Programación (4 casos) ───────────────────────────────────

    {
        "id": 23,
        "topic": "Variable",
        "desc": "Respuesta completa (los 4 conceptos)",
        "reference": _REF_VARIABLE,
        "student_answer": (
            "Una variable es una zona de memoria identificada por un nombre "
            "que guarda un valor de un tipo concreto."
        ),
        # memoria ✓  nombre ✓  valor ✓  tipo ✓ → concept_ratio=1.0
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 24,
        "topic": "Variable",
        "desc": "Respuesta parcial (sin tipo)",
        "reference": _REF_VARIABLE,
        "student_answer": (
            "Una variable es un espacio en memoria con un nombre asociado "
            "donde podemos guardar valores."
        ),
        # memoria ✓  nombre ✓  valor ✓  tipo ✗ → concept_ratio=0.75 → floor=0.6
        "nota_min": 5.5,
        "nota_max": 8.5,
    },
    {
        "id": 25,
        "topic": "Variable",
        "desc": "Vocabulario adyacente (datos/contenedor en lugar de los términos técnicos)",
        "reference": _REF_VARIABLE,
        "student_answer": (
            "Una variable es como un contenedor donde se pueden meter datos "
            "y reutilizarlos a lo largo del programa."
        ),
        # ningún concepto literal: "contenedor"≠memoria, "datos"≠valor,
        # "tipo" y "nombre" no aparecen → concept_ratio≈0
        "nota_min": 0.0,
        "nota_max": 3.0,
    },
    {
        "id": 26,
        "topic": "Variable",
        "desc": "Respuesta trivial",
        "reference": _REF_VARIABLE,
        "student_answer": "Una variable es algo que se usa en programación.",
        # ningún concepto técnico → concept_ratio=0
        "nota_min": 0.0,
        "nota_max": 2.0,
    },

    # ── Complejidad temporal / Algoritmos (3 casos) ─────────────────────────

    {
        "id": 27,
        "topic": "Complejidad temporal",
        "desc": "Respuesta completa (los 4 conceptos)",
        "reference": _REF_COMPLEJIDAD,
        "student_answer": (
            "La complejidad temporal mide el tiempo de ejecución de un algoritmo "
            "en función del tamaño de la entrada. Se expresa con notación Big-O "
            "para caracterizar el peor caso asintótico."
        ),
        # tiempo ✓  entrada ✓  asintótico ✓  peor caso ✓ → concept_ratio=1.0
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 28,
        "topic": "Complejidad temporal",
        "desc": "Respuesta parcial (sin notación asintótica ni peor caso)",
        "reference": _REF_COMPLEJIDAD,
        "student_answer": (
            "La complejidad temporal es el tiempo que tarda un algoritmo "
            "en función del tamaño de los datos de entrada."
        ),
        # tiempo ✓  entrada ✓  asintótico ✗  peor caso ✗ → concept_ratio=0.45
        "nota_min": 2.5,
        "nota_max": 5.5,
    },
    {
        "id": 29,
        "topic": "Complejidad temporal",
        "desc": "Vocabulario alternativo correcto pero sin los términos exactos de la rúbrica",
        "reference": _REF_COMPLEJIDAD,
        "student_answer": (
            "La complejidad temporal es la cantidad de operaciones que ejecuta "
            "un algoritmo conforme aumenta el tamaño de la entrada. Suele "
            "expresarse con la O grande del peor caso."
        ),
        # "operaciones"≠tiempo (sequencematcher bajo), entrada ✓, peor caso ✓,
        # asintótico ✗ ("O grande" no matchea) → concept_ratio≈0.45
        # Caso ilustrativo: respuesta técnicamente correcta penalizada por
        # falta de literalidad. Sin synonym_map para "tiempo"/"operaciones".
        "nota_min": 3.0,
        "nota_max": 6.0,
    },

    # ── HTTP / Redes (3 casos) ──────────────────────────────────────────────

    {
        "id": 30,
        "topic": "HTTP",
        "desc": "Respuesta completa (los 4 conceptos)",
        "reference": _REF_HTTP,
        "student_answer": (
            "HTTP es un protocolo de la capa de aplicación usado por los "
            "clientes y servidores web para intercambiar peticiones y "
            "respuestas con los recursos hipertexto."
        ),
        # protocolo ✓  cliente ✓  servidor ✓  petición ✓ → concept_ratio=1.0
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 31,
        "topic": "HTTP",
        "desc": "Respuesta parcial (omite el modelo cliente-servidor)",
        "reference": _REF_HTTP,
        "student_answer": (
            "HTTP es el protocolo que define el formato de las peticiones "
            "que viajan por Internet para cargar páginas web."
        ),
        # protocolo ✓  petición ✓  cliente ✗  servidor ✗ → concept_ratio=0.50
        "nota_min": 3.0,
        "nota_max": 6.0,
    },
    {
        "id": 32,
        "topic": "HTTP",
        "desc": "Respuesta trivial",
        "reference": _REF_HTTP,
        "student_answer": "HTTP es algo de Internet que sirve para que las webs funcionen.",
        # ningún concepto técnico → concept_ratio=0
        "nota_min": 0.0,
        "nota_max": 2.0,
    },

    # ── Clave primaria / Bases de datos (3 casos) ───────────────────────────

    {
        "id": 33,
        "topic": "Clave primaria",
        "desc": "Respuesta completa (los 4 conceptos)",
        "reference": _REF_CLAVE_PRIMARIA,
        "student_answer": (
            "La clave primaria es uno o varios campos que identifican de forma "
            "única cada fila de una tabla, y no pueden tener valor nulo."
        ),
        # única ✓  tabla ✓  fila ✓  nulo ✓ → concept_ratio=1.0
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 34,
        "topic": "Clave primaria",
        "desc": "Respuesta parcial (sin la restricción NOT NULL)",
        "reference": _REF_CLAVE_PRIMARIA,
        "student_answer": (
            "La clave primaria es un atributo de una tabla que identifica "
            "de manera única cada fila."
        ),
        # única ✓  tabla ✓  fila ✓  nulo ✗ → concept_ratio=0.75 → floor=0.6
        "nota_min": 5.5,
        "nota_max": 8.5,
    },
    {
        "id": 35,
        "topic": "Clave primaria",
        "desc": "Respuesta trivial",
        "reference": _REF_CLAVE_PRIMARIA,
        "student_answer": "La clave primaria es algo muy importante en las bases de datos.",
        # ningún concepto técnico → concept_ratio=0
        "nota_min": 0.0,
        "nota_max": 2.0,
    },

    # ── Robustez: NEGACIÓN y polaridad (5 casos) ─────────────────────────────
    # El grader detecta presencia de conceptos; estos casos comprueban que
    # ANTES de acreditarlos analiza la polaridad, para no premiar respuestas
    # que niegan lo correcto ni castigar negaciones legítimas de otra cosa.
    {
        "id": 36,
        "topic": "Negación",
        "desc": "Niega los conceptos correctos (debe suspender pese a las palabras)",
        "reference": _REF_MITOCONDRIA,
        "student_answer": (
            "La mitocondria NO produce energía ni ATP y tampoco realiza la "
            "respiración celular; de eso se encarga el núcleo."
        ),
        # Todos los conceptos aparecen pero NEGADOS → no se acreditan.
        "nota_min": 0.0,
        "nota_max": 3.5,
    },
    {
        "id": 37,
        "topic": "Negación",
        "desc": "Atribución correcta con negación de OTRO orgánulo (no debe penalizar)",
        "reference": _REF_MITOCONDRIA,
        "student_answer": (
            "A diferencia del cloroplasto, que no hace la respiración, la "
            "mitocondria sí produce energía en forma de ATP mediante la "
            "respiración celular."
        ),
        # La negación recae sobre el cloroplasto, no sobre los conceptos → ALTA.
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 38,
        "topic": "Negación",
        "desc": "Construcción enfática 'no solo ... sino' (no es negación)",
        "reference": _REF_MITOCONDRIA,
        "student_answer": (
            "La mitocondria no solo produce energía, sino que genera ATP "
            "mediante la respiración celular en el orgánulo."
        ),
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 39,
        "topic": "Negación",
        "desc": "Restricción NOT NULL correcta ('no nulo' es la respuesta buena)",
        "reference": _REF_CLAVE_PRIMARIA,
        "student_answer": (
            "Una clave primaria identifica de forma única cada fila de una "
            "tabla y su valor no puede ser nulo."
        ),
        "nota_min": 8.0,
        "nota_max": 10.0,
    },
    {
        "id": 40,
        "topic": "Negación",
        "desc": "Afirma que SÍ puede ser nulo (incorrecto: no debe acreditar 'no nulo')",
        "reference": _REF_CLAVE_PRIMARIA,
        "student_answer": (
            "Una clave primaria identifica cada fila de una tabla de forma "
            "única y puede tener valor nulo sin problema."
        ),
        # 'no nulo' no se acredita (afirma lo contrario) → 3 de 4 conceptos.
        # El grader determinista no la castiga MÁS por la afirmación falsa (eso
        # corresponde al verificador LLM opcional); solo no le da ese concepto,
        # por lo que queda por debajo de la respuesta completa (caso 39).
        "nota_min": 4.0,
        "nota_max": 8.0,
    },
]


# ── Runner ────────────────────────────────────────────────────────────────────

def _empty_bucket() -> dict:
    return {"pass": 0, "expected_fail": 0, "unexpected_fail": 0, "total": 0}


def _print_breakdown(title: str, buckets: dict, label_width: int) -> None:
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)
    for key in sorted(buckets):
        b = buckets[key]
        conformant = b["pass"] + b["expected_fail"]
        pct = conformant / b["total"] * 100 if b["total"] else 0.0
        line = (
            f"  {key:<{label_width}}  "
            f"{b['pass']:>2} PASS · {b['expected_fail']} esperado · "
            f"{b['unexpected_fail']} inesperado  "
            f"({conformant}/{b['total']}, {pct:3.0f}%)"
        )
        print(line)


def run_validation() -> None:
    grader = SemanticGrader()
    passed = 0
    expected_fails = 0
    unexpected_fails = 0
    total = len(TEST_CASES)

    per_topic = defaultdict(_empty_bucket)
    per_subject = defaultdict(_empty_bucket)

    print("=" * 72)
    print(f"{'VALIDATE — Sistema de Corrección Semántica':^72}")
    print(f"{f'{total} casos · Biología y Informática':^72}")
    print("=" * 72)

    for case in TEST_CASES:
        result = grader.grade(case["student_answer"], case["reference"])
        score = result["score_over_10"]
        ok = case["nota_min"] <= score <= case["nota_max"]
        expected_to_fail = case.get("expected_to_fail", False)

        if ok:
            tag = "PASS ✓"
            passed += 1
            bucket_key = "pass"
        elif expected_to_fail:
            tag = "FAIL esperado ⚠"
            expected_fails += 1
            bucket_key = "expected_fail"
        else:
            tag = "FAIL ✗"
            unexpected_fails += 1
            bucket_key = "unexpected_fail"

        topic = case["topic"]
        subject = case["reference"].subject
        per_topic[topic][bucket_key] += 1
        per_topic[topic]["total"] += 1
        per_subject[subject][bucket_key] += 1
        per_subject[subject]["total"] += 1

        snippet = case["student_answer"]
        if len(snippet) > 65:
            snippet = snippet[:65] + "…"

        print(
            f"\n[{case['id']:02d}] {case['topic']} | {case['desc']}\n"
            f"     Respuesta  : {snippet!r}\n"
            f"     Nota       : {score:5.2f}  "
            f"(rango esperado {case['nota_min']:.1f}–{case['nota_max']:.1f})  "
            f"→ {tag}"
        )
        if not ok:
            print(
                f"     Detectados : {result['detected_concepts']}\n"
                f"     Faltantes  : {result['missing_concepts']}\n"
                f"     Parciales  : {result['partial_concepts']}"
            )

    conformant = passed + expected_fails
    pct = conformant / total * 100
    verdict = "OK" if unexpected_fails == 0 else f"{unexpected_fails} fallo(s) inesperado(s)"

    topic_width = max(len(k) for k in per_topic)
    subject_width = max(len(k) for k in per_subject)

    print("\n")
    _print_breakdown("ACCURACY POR TEMA", per_topic, topic_width)
    print()
    _print_breakdown("ACCURACY POR ASIGNATURA", per_subject, subject_width)

    print("\n" + "=" * 72)
    print(
        f"  TOTAL: {passed} PASS · {expected_fails} FAIL esperado · "
        f"{unexpected_fails} FAIL inesperado  ·  "
        f"{pct:.0f}% comportamiento conforme  ·  {verdict}"
    )
    print("=" * 72)


if __name__ == "__main__":
    run_validation()

"""
validate.py — 22 test cases for the semantic grading system.

Run from the src/ directory:
    python validate.py

Or from the project root:
    python src/validate.py

Prints each case with its score, expected range, and PASS/FAIL.
Finishes with total passed and accuracy percentage.
"""

from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader


# ── Helper ────────────────────────────────────────────────────────────────────

def _ref(question: str, ideal_answer: str, key_concepts: list) -> ReferenceAnswer:
    return ReferenceAnswer(
        question=question,
        subject="Biología",
        education_level="Bachillerato",
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
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_validation() -> None:
    grader = SemanticGrader()
    passed = 0
    expected_fails = 0
    unexpected_fails = 0
    total = len(TEST_CASES)

    print("=" * 72)
    print(f"{'VALIDATE — Sistema de Corrección Semántica':^72}")
    print(f"{'22 casos · Biología básica':^72}")
    print("=" * 72)

    for case in TEST_CASES:
        result = grader.grade(case["student_answer"], case["reference"])
        score = result["score_over_10"]
        ok = case["nota_min"] <= score <= case["nota_max"]
        expected_to_fail = case.get("expected_to_fail", False)

        if ok:
            tag = "PASS ✓"
            passed += 1
        elif expected_to_fail:
            tag = "FAIL esperado ⚠"
            expected_fails += 1
        else:
            tag = "FAIL ✗"
            unexpected_fails += 1

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
    print("\n" + "=" * 72)
    print(
        f"  {passed} PASS · {expected_fails} FAIL esperado · "
        f"{unexpected_fails} FAIL inesperado  ·  "
        f"{pct:.0f}% comportamiento conforme  ·  {verdict}"
    )
    print("=" * 72)


if __name__ == "__main__":
    run_validation()

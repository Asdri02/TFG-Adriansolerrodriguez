"""
Tests del análisis de POLARIDAD del SemanticGrader: un concepto solo se acredita
si el alumno lo AFIRMA. Negarlo ("la mitocondria NO produce ATP") no debe sumar,
pero negar OTRA cosa o usar construcciones enfáticas ("no solo... sino") sí.

Pura lógica determinista, sin web ni LLM.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader


def _ref():
    return ReferenceAnswer(
        question="¿Cuál es la función de la mitocondria?",
        subject="Biología", education_level="Bachillerato",
        expected_answer_type="respuesta_corta",
        ideal_answer="La mitocondria produce ATP mediante la respiración celular.",
        key_concepts=[
            {"concept": "respiración celular", "weight": 0.4},
            {"concept": "ATP", "weight": 0.3},
            {"concept": "fosforilación oxidativa", "weight": 0.3},
        ],
    )


@pytest.fixture
def grader():
    return SemanticGrader()


# ── concept_polarity en aislamiento ──────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("la mitocondria produce atp", "affirmed"),
    ("la mitocondria no produce atp", "negated"),
    ("la mitocondria nunca produce atp", "negated"),
    ("ni produce atp ni respira", "negated"),
    ("no solo produce atp sino mucho mas", "affirmed"),   # enfático, no negación
    ("aqui no se habla de eso", "absent"),                # el concepto no aparece
])
def test_concept_polarity_atp(grader, text, expected):
    clauses = grader.split_clauses(text)
    assert grader.concept_polarity("atp", clauses) == expected


def test_negacion_no_cruza_limite_de_clausula(grader):
    # La negación afecta al cloroplasto, no al ATP (cláusulas distintas).
    clauses = grader.split_clauses(
        "el cloroplasto no produce atp, pero la mitocondria si produce atp"
    )
    assert grader.concept_polarity("atp", clauses) == "affirmed"


# ── grade() de extremo a extremo ─────────────────────────────────────────────

def test_negar_todo_no_acredita_conceptos(grader):
    out = grader.grade(
        "La mitocondria NO realiza la respiración celular ni produce ATP.", _ref()
    )
    assert set(out["negated_concepts"]) >= {"respiración celular", "ATP"}
    assert out["score_over_10"] < 4.0


def test_afirmar_todo_puntua_alto(grader):
    out = grader.grade(
        "La mitocondria produce ATP mediante la respiración celular y la "
        "fosforilación oxidativa.", _ref()
    )
    assert out["negated_concepts"] == []
    assert out["score_over_10"] >= 8.0


def test_negacion_de_otro_organulo_no_penaliza(grader):
    out = grader.grade(
        "A diferencia del cloroplasto, que no hace la respiración, la mitocondria "
        "sí produce ATP por respiración celular y fosforilación oxidativa.", _ref()
    )
    assert out["negated_concepts"] == []
    assert out["score_over_10"] >= 8.0


def test_no_solo_no_es_negacion(grader):
    out = grader.grade(
        "La mitocondria no solo produce ATP, sino que realiza la respiración "
        "celular y la fosforilación oxidativa.", _ref()
    )
    assert out["negated_concepts"] == []
    assert out["score_over_10"] >= 8.0


def test_no_metales_no_es_negacion(grader):
    """'no metales' es un término químico, no una negación: no debe negar los
    conceptos que aparezcan después en la misma cláusula (regresión del banco)."""
    ref = ReferenceAnswer(
        question="¿Qué es el enlace covalente?",
        subject="Química", education_level="Bachillerato",
        expected_answer_type="respuesta_corta",
        ideal_answer="Dos no metales comparten pares de electrones para formar una molécula.",
        key_concepts=[
            {"concept": "no metales", "weight": 0.3},
            {"concept": "pares de electrones", "weight": 0.4},
            {"concept": "molécula", "weight": 0.3},
        ],
    )
    out = grader.grade(
        "Dos no metales comparten pares de electrones para formar una molécula como el agua.",
        ref,
    )
    assert out["negated_concepts"] == []
    assert "pares de electrones" in out["detected_concepts"]
    assert "molécula" in out["detected_concepts"]
    assert out["score_over_10"] >= 8.0

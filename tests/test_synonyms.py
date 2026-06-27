"""
Tests de los SINÓNIMOS por concepto: una paráfrasis declarada por el profesor
acredita el concepto aunque el alumno no use el término exacto, con tolerancia
morfológica, sin inflar respuestas que niegan el concepto y sin afectar a
conceptos que no declaran sinónimos.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.models import ReferenceAnswer
from ai.semantic_grader import SemanticGrader


@pytest.fixture
def grader():
    return SemanticGrader()


def _ref_lifo(synonyms):
    return ReferenceAnswer(
        question="¿Qué es una pila?",
        subject="Estructuras de Datos", education_level="Universidad",
        expected_answer_type="respuesta_corta",
        ideal_answer="Una pila es una estructura LIFO.",
        key_concepts=[{"concept": "LIFO", "weight": 1.0, "synonyms": synonyms}],
    )


# ── synonym_matches en aislamiento ───────────────────────────────────────────

def test_synonym_substring(grader):
    norm = grader.normalize_text("usa una estructura lifo interna")
    toks = grader.tokenize("usa una estructura lifo interna")
    assert grader.synonym_matches("LIFO", norm, toks) is True


def test_synonym_tokens_con_tolerancia_morfologica(grader):
    # "metes/sacas" ≈ "meter/sacar" por el umbral fuzzy 0.80
    txt = "el último que metes es el primero que sacas"
    norm, toks = grader.normalize_text(txt), grader.tokenize(txt)
    assert grader.synonym_matches("último en meter primero en sacar", norm, toks) is True


def test_synonym_no_casa_si_falta_un_token_de_contenido(grader):
    txt = "una cola FIFO del supermercado"
    norm, toks = grader.normalize_text(txt), grader.tokenize(txt)
    assert grader.synonym_matches("último en entrar primero en salir", norm, toks) is False


# ── grade() de extremo a extremo ─────────────────────────────────────────────

def test_parafrasis_acredita_el_concepto(grader):
    ref = _ref_lifo(["último en entrar primero en salir", "último en meter primero en sacar"])
    out = grader.grade("Es una estructura donde el último que metes es el primero que sacas.", ref)
    assert "LIFO" in out["detected_concepts"]
    assert out["score_over_10"] >= 8.0


def test_sin_sinonimos_no_detecta_la_parafrasis(grader):
    # mismo texto, pero el concepto NO declara sinónimos → comportamiento literal
    ref = _ref_lifo([])
    out = grader.grade("Es una estructura donde el último que metes es el primero que sacas.", ref)
    assert "LIFO" not in out["detected_concepts"]
    assert out["score_over_10"] < 3.0


def test_sinonimo_negado_no_acredita(grader):
    ref = ReferenceAnswer(
        question="¿Qué es el aprendizaje supervisado?",
        subject="IA", education_level="Universidad",
        expected_answer_type="respuesta_corta",
        ideal_answer="Aprende de datos etiquetados.",
        key_concepts=[{"concept": "datos etiquetados", "weight": 1.0,
                       "synonyms": ["datos con etiquetas", "etiquetas"]}],
    )
    out = grader.grade("El modelo aprende sin ningún dato ni etiqueta.", ref)
    assert "datos etiquetados" in out["negated_concepts"]
    assert out["score_over_10"] < 3.0


def test_phrase_polarity_directo(grader):
    clauses = grader.split_clauses("aprende sin ningún dato ni etiqueta")
    assert grader.phrase_polarity("etiquetas", clauses) == "negated"
    clauses2 = grader.split_clauses("aprende con muchas etiquetas")
    assert grader.phrase_polarity("etiquetas", clauses2) == "affirmed"

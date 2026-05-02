"""
reference_db.py — Cached reference-answer store for the semantic grader.

get_reference(question) → ReferenceAnswer
  1. Looks up data/reference_cache.json for an existing entry.
  2. On cache miss, calls Claude to generate ideal_answer + key_concepts with weights.
  3. Persists the new entry and returns a ReferenceAnswer ready for SemanticGrader.grade().

Cache JSON structure
--------------------
{
  "<question text>": {
    "ideal_answer": "...",
    "key_concepts": [
      {"concept": "...", "weight": 0.40},
      ...
    ],
    "common_mistakes": ["...", ...],
    "rubric": [{"criterion": "...", "points": 1.0}, ...],
    "confidence": 0.9
  },
  ...
}

Note: key_concepts is stored — and returned — as List[Dict] with "concept" and "weight"
keys, matching the format expected by SemanticGrader.concept_match_score().
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import anthropic

from ai.models import ReferenceAnswer, RubricItem

# ── paths ────────────────────────────────────────────────────────────────────

_SRC_DIR = Path(__file__).parent
_CACHE_PATH = _SRC_DIR.parent / "data" / "reference_cache.json"

# ── cache helpers ─────────────────────────────────────────────────────────────


def _load_cache() -> Dict[str, Any]:
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=2)


# ── LLM generation ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Eres un asistente académico especializado en generar referencias de corrección.

Tu tarea: dada una pregunta de examen, devuelve ÚNICAMENTE JSON válido (sin bloques
de código, sin texto adicional) con esta estructura exacta:

{
  "ideal_answer": "<respuesta modelo completa en el mismo idioma que la pregunta>",
  "key_concepts": [
    {"concept": "<término o frase clave>", "weight": <float 0-1>},
    ...
  ],
  "common_mistakes": ["<error frecuente 1>", "<error frecuente 2>"],
  "rubric": [
    {"criterion": "<criterio de corrección>", "points": <float>},
    ...
  ],
  "confidence": <float 0-1>
}

CRITERIOS DE CALIBRACIÓN:
- La rúbrica debe ser adecuada al nivel educativo indicado.
- Si el nivel es ESO o Bachillerato, NO incluyas conceptos universitarios o de gran detalle bioquímico (ej: ciclos metabólicos específicos por nombre, vías moleculares avanzadas, regulación iónica fina).
- Los conceptos clave deben ser los que un alumno de ese nivel debería saber para responder correctamente, no los que un experto añadiría.
- Máximo 5 conceptos clave. Mejor 4-5 conceptos centrales y bien ponderados que 8 conceptos diluidos.
- Cada "concept" de key_concepts debe ser un término CORTO (1-3 palabras) que un alumno escribiría literalmente en su respuesta. NO frases descriptivas. Ejemplo correcto: "ATP", "respiración celular", "mitocondria", "ADN", "energía". Ejemplo INCORRECTO: "Producción de ATP y energía celular", "Estructura con membranas y crestas mitocondriales".

Reglas:
- key_concepts: entre 4 y 5 conceptos, pesos sumando exactamente 1.0, ordenados por importancia.
- rubric: puntos totales sumando 10.0.
- Responde en el mismo idioma que la pregunta.

IMPORTANTE: devuelve únicamente el JSON crudo, sin envolver en bloques de código markdown. Solo el objeto JSON.
""".strip()


def _strip_markdown_fence(raw: str) -> str:
    """Remove markdown code fences if Claude wraps the JSON in them."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1:]
        if stripped.endswith("```"):
            stripped = stripped[:-3].rstrip()
    return stripped


def _cache_key(question: str, subject: str, education_level: str) -> str:
    return f"{question}|{subject}|{education_level}"


def _generate_from_llm(
    question: str,
    subject: str,
    education_level: str,
) -> Dict[str, Any]:
    """Call Claude and return the parsed JSON entry."""
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Materia: {subject}\n"
                    f"Nivel educativo: {education_level}\n\n"
                    f"Genera la referencia de corrección para esta pregunta:\n\n"
                    f"{question}"
                ),
            }
        ],
    )

    raw = response.content[0].text

    try:
        data = json.loads(_strip_markdown_fence(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Claude devolvió JSON inválido para la pregunta «{question}».\n"
            f"Respuesta bruta:\n{raw}"
        ) from exc

    for field in ("ideal_answer", "key_concepts", "common_mistakes", "rubric", "confidence"):
        if field not in data:
            raise ValueError(f"Falta el campo obligatorio '{field}' en la respuesta de Claude.")

    return data


# ── public API ────────────────────────────────────────────────────────────────


def get_reference(
    question: str,
    subject: str = "General",
    education_level: str = "Bachillerato",
) -> ReferenceAnswer:
    """
    Return a ReferenceAnswer for *question*, generating and caching it if needed.

    The cache key is composed of (question, subject, education_level) so that
    distinct calibrations can coexist.

    Compatible with SemanticGrader.grade(): the returned object's key_concepts is
    List[Dict] where each dict has "concept" (str) and "weight" (float), as required
    by SemanticGrader.concept_match_score().
    """
    question = question.strip()
    key = _cache_key(question, subject, education_level)
    cache = _load_cache()

    if key not in cache:
        entry = _generate_from_llm(question, subject, education_level)
        cache[key] = entry
        _save_cache(cache)

    entry = cache[key]

    return ReferenceAnswer(
        question=question,
        subject=subject,
        education_level=education_level,
        expected_answer_type="respuesta_abierta",
        ideal_answer=entry["ideal_answer"],
        # key_concepts stored as List[Dict] — matches SemanticGrader.concept_match_score()
        key_concepts=entry["key_concepts"],
        rubric=[
            RubricItem(criterion=item["criterion"], points=float(item["points"]))
            for item in entry.get("rubric", [])
        ],
        common_mistakes=entry.get("common_mistakes", []),
        confidence=float(entry.get("confidence", 0.0)),
    )


def invalidate(question: str) -> bool:
    """
    Remove every cached entry for *question* (across any subject/education_level
    variant, plus the legacy single-key format), forcing regeneration on the
    next call.

    Returns True if at least one entry was removed, False otherwise.
    """
    question = question.strip()
    cache = _load_cache()
    keys_to_remove = [
        k for k in cache
        if k == question or k.startswith(f"{question}|")
    ]
    for k in keys_to_remove:
        del cache[k]
    if keys_to_remove:
        _save_cache(cache)
        return True
    return False


def list_cached_questions() -> List[str]:
    """Return all questions currently in the cache."""
    return list(_load_cache().keys())

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

Reglas:
- key_concepts: entre 4 y 8 conceptos, pesos sumando exactamente 1.0, ordenados por importancia.
- rubric: puntos totales sumando 10.0.
- Responde en el mismo idioma que la pregunta.
""".strip()


def _generate_from_llm(question: str) -> Dict[str, Any]:
    """Call Claude and return the parsed JSON entry."""
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Genera la referencia de corrección para esta pregunta:\n\n"
                    f"{question}"
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()

    try:
        data = json.loads(raw)
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


def get_reference(question: str) -> ReferenceAnswer:
    """
    Return a ReferenceAnswer for *question*, generating and caching it if needed.

    Compatible with SemanticGrader.grade(): the returned object's key_concepts is
    List[Dict] where each dict has "concept" (str) and "weight" (float), as required
    by SemanticGrader.concept_match_score().

    Parameters
    ----------
    question : str
        The exam question, used as the cache key (stripped).

    Returns
    -------
    ReferenceAnswer
        Populated with ideal_answer, key_concepts (weighted), rubric, common_mistakes,
        and confidence. subject / education_level / expected_answer_type are left as
        empty strings — enrich them at the call site if needed.
    """
    question = question.strip()
    cache = _load_cache()

    if question not in cache:
        entry = _generate_from_llm(question)
        cache[question] = entry
        _save_cache(cache)

    entry = cache[question]

    return ReferenceAnswer(
        question=question,
        subject="",
        education_level="",
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
    Remove *question* from the cache, forcing regeneration on the next call.

    Returns True if the entry existed and was removed, False otherwise.
    """
    question = question.strip()
    cache = _load_cache()
    if question in cache:
        del cache[question]
        _save_cache(cache)
        return True
    return False


def list_cached_questions() -> List[str]:
    """Return all questions currently in the cache."""
    return list(_load_cache().keys())

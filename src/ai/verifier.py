"""
verifier.py — Verificación de FACTUALIDAD como segunda opinión opcional.

El SemanticGrader es determinista e interpretable, pero solo mide presencia y
polaridad local de los conceptos. No puede detectar una ATRIBUCIÓN ERRÓNEA del
tipo "la respiración celular y el ATP son cosas del cloroplasto", donde los
términos aparecen afirmados pero referidos al orgánulo equivocado.

Este módulo añade una capa OPCIONAL: un LLM revisa, concepto a concepto, si la
respuesta del alumno lo afirma correctamente, lo niega, lo atribuye mal o lo
omite, y si el conjunto contiene una contradicción factual.

Filosofía (coherente con el TFG): el verificador NO sustituye ni reescribe la
nota determinista. Devuelve una SEÑAL ("revisar: posible atribución errónea")
para que el profesor decida. Así el sistema sigue siendo trazable: se ve qué
nota dio el grader, qué marcó el verificador y por qué.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

_MODEL = "claude-haiku-4-5"

_VALID_STATUS = {"correcto", "negado", "atribucion_erronea", "ausente"}


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    return raw


def verify_factuality(
    question: str,
    ideal_answer: str,
    key_concepts: List[Dict[str, Any]],
    student_answer: str,
) -> Dict[str, Any]:
    """
    Pide al LLM que clasifique cada concepto clave en la respuesta del alumno.

    Devuelve:
      {
        "contradiction": bool,              # ¿hay una afirmación factualmente falsa?
        "concepts": [{"concept", "status", "comment"}],
        "flagged": [conceptos con status != "correcto" pero presentes],
        "advice": "<recomendación breve para el profesor>",
        "method": "llm_verifier",
      }

    `status` ∈ {correcto, negado, atribucion_erronea, ausente}.
    Lanza RuntimeError si el LLM no está disponible o devuelve algo no parseable;
    el llamante decide si degradar a "solo determinista".
    """
    concepts_block = "\n".join(
        f"  - {c['concept']}" for c in key_concepts
    ) or "  (sin conceptos)"

    system_prompt = (
        "Eres un corrector experto que verifica la FACTUALIDAD de una respuesta de "
        "examen. No pones nota: clasificas cómo trata el alumno cada concepto clave. "
        "Devuelves ÚNICAMENTE JSON válido, sin markdown."
    )
    user_prompt = (
        f"PREGUNTA: {question}\n"
        f"RESPUESTA IDEAL: {ideal_answer}\n\n"
        f"CONCEPTOS CLAVE A VERIFICAR:\n{concepts_block}\n\n"
        f"RESPUESTA DEL ALUMNO:\n«{student_answer.strip()}»\n\n"
        "Para CADA concepto clave indica su 'status' según cómo lo trate el alumno:\n"
        "  - \"correcto\": lo afirma y lo aplica correctamente.\n"
        "  - \"negado\": lo niega o dice que no ocurre.\n"
        "  - \"atribucion_erronea\": usa el término pero lo asigna a algo equivocado "
        "(otro órgano, proceso, autor, etc.).\n"
        "  - \"ausente\": no aparece.\n\n"
        "Devuelve JSON EXACTO:\n"
        '{\n'
        '  "contradiction": <true|false>,\n'
        '  "concepts": [{"concept": "<texto>", "status": "<correcto|negado|'
        'atribucion_erronea|ausente>", "comment": "<breve>"}],\n'
        '  "advice": "<una frase para el profesor>"\n'
        '}'
    )

    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=_MODEL,
            temperature=0,
            max_tokens=700,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        data = json.loads(_strip_fences(resp.content[0].text))
    except Exception as exc:  # noqa: BLE001 — el llamante decide el fallback
        raise RuntimeError(f"verificador LLM no disponible: {type(exc).__name__}: {exc}")

    concepts = []
    for c in data.get("concepts", []):
        status = str(c.get("status", "")).strip().lower()
        if status not in _VALID_STATUS:
            status = "ausente"
        concepts.append({
            "concept": c.get("concept", ""),
            "status": status,
            "comment": c.get("comment", ""),
        })

    # "flagged": conceptos que el grader podría haber contado pero que el
    # verificador considera negados o mal atribuidos (presentes pero incorrectos).
    flagged = [c for c in concepts if c["status"] in ("negado", "atribucion_erronea")]

    return {
        "contradiction": bool(data.get("contradiction", False)),
        "concepts": concepts,
        "flagged": flagged,
        "advice": data.get("advice", ""),
        "method": "llm_verifier",
    }

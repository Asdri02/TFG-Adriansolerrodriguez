import json
from typing import Any, Dict

from ai.models import ReferenceAnswer, RubricItem


class PromptBuilder:
    @staticmethod
    def build(
        question: str,
        subject: str,
        education_level: str,
        expected_answer_type: str,
    ) -> str:
        return f"""
Eres un asistente académico especializado en generar referencias de corrección.

Tu tarea es leer una pregunta de examen y devolver:
1. Una respuesta ideal breve y correcta.
2. Una lista de conceptos clave imprescindibles.
3. Una rúbrica de corrección con criterios y puntos.
4. Una lista de errores frecuentes.
5. Un valor de confianza entre 0 y 1.

Devuelve exclusivamente JSON válido con esta estructura:
{{
  "ideal_answer": "texto",
  "key_concepts": ["c1", "c2", "c3"],
  "rubric": [
    {{"criterion": "criterio 1", "points": 1.0}},
    {{"criterion": "criterio 2", "points": 1.0}}
  ],
  "common_mistakes": ["e1", "e2"],
  "confidence": 0.85
}}

Materia: {subject}
Nivel educativo: {education_level}
Tipo de respuesta esperada: {expected_answer_type}
Pregunta: {question}
""".strip()


class ReferenceGenerator:
    """
    Clase preparada para conectar con un LLM real.
    De momento espera que una subclase implemente _call_model().
    """

    def generate(
        self,
        question: str,
        subject: str = "General",
        education_level: str = "Universidad",
        expected_answer_type: str = "respuesta_corta",
    ) -> ReferenceAnswer:
        prompt = PromptBuilder.build(
            question=question,
            subject=subject,
            education_level=education_level,
            expected_answer_type=expected_answer_type,
        )

        raw_response = self._call_model(prompt)
        parsed = self._parse_response(raw_response)

        return ReferenceAnswer(
            question=question,
            subject=subject,
            education_level=education_level,
            expected_answer_type=expected_answer_type,
            ideal_answer=parsed["ideal_answer"],
            key_concepts=parsed["key_concepts"],
            rubric=[
                RubricItem(item["criterion"], float(item["points"]))
                for item in parsed["rubric"]
            ],
            common_mistakes=parsed["common_mistakes"],
            confidence=float(parsed["confidence"]),
        )

    def _call_model(self, prompt: str) -> str:
        raise NotImplementedError(
            "Debes implementar _call_model() para conectar un modelo real."
        )

    @staticmethod
    def _parse_response(raw_response: str) -> Dict[str, Any]:
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"La respuesta del modelo no es JSON válido: {exc}") from exc

        required_fields = [
            "ideal_answer",
            "key_concepts",
            "rubric",
            "common_mistakes",
            "confidence",
        ]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Falta el campo obligatorio: {field}")

        return data
from ai.models import ReferenceAnswer, RubricItem


class MockReferenceGenerator:
    def generate(
        self,
        question: str,
        subject: str = "General",
        education_level: str = "Universidad",
        expected_answer_type: str = "respuesta_corta",
    ) -> ReferenceAnswer:
        question_lower = question.lower()

        if "mitocondria" in question_lower:
            return ReferenceAnswer(
                question=question,
                subject=subject,
                education_level=education_level,
                expected_answer_type=expected_answer_type,
                ideal_answer=(
                    "La mitocondria es un orgánulo celular encargado de producir "
                    "energía en forma de ATP mediante la respiración celular."
                ),
                key_concepts=[
                    {"concept": "mitocondria", "weight": 1.0},
                    {"concept": "energía", "weight": 1.0},
                    {"concept": "ATP", "weight": 0.5},
                    {"concept": "respiración celular", "weight": 0.5},
                ],
                rubric=[
                    RubricItem("Identifica la mitocondria como orgánulo celular", 1.0),
                    RubricItem("Menciona la producción de energía", 1.0),
                    RubricItem("Menciona ATP", 0.5),
                    RubricItem("Relaciona la función con la respiración celular", 0.5),
                ],
                common_mistakes=[
                    "Confundir la mitocondria con el núcleo",
                    "No mencionar energía",
                    "No relacionarla con la respiración celular",
                ],
                confidence=0.95,
            )

        if "revolución francesa" in question_lower:
            return ReferenceAnswer(
                question=question,
                subject=subject,
                education_level=education_level,
                expected_answer_type=expected_answer_type,
                ideal_answer=(
                    "La Revolución Francesa fue un proceso político y social iniciado en 1789 "
                    "que puso fin al Antiguo Régimen en Francia y promovió ideas como "
                    "libertad, igualdad y soberanía nacional."
                ),
                key_concepts=[
                    {"concept": "1789", "weight": 0.75},
                    {"concept": "Francia", "weight": 0.75},
                    {"concept": "Antiguo Régimen", "weight": 1.0},
                    {"concept": "libertad", "weight": 0.5},
                    {"concept": "igualdad", "weight": 0.5},
                    {"concept": "soberanía nacional", "weight": 0.5},
                ],
                rubric=[
                    RubricItem("Sitúa el proceso en Francia", 0.75),
                    RubricItem("Menciona el inicio en 1789", 0.75),
                    RubricItem("Explica el fin del Antiguo Régimen", 1.0),
                    RubricItem("Incluye ideas principales de la revolución", 1.0),
                ],
                common_mistakes=[
                    "No indicar la fecha de inicio",
                    "Reducirla solo a una guerra",
                    "No mencionar los cambios políticos o sociales",
                ],
                confidence=0.92,
            )

        return ReferenceAnswer(
            question=question,
            subject=subject,
            education_level=education_level,
            expected_answer_type=expected_answer_type,
            ideal_answer=(
                "Respuesta de referencia provisional generada para una pregunta general. "
                "Debe revisarse o sustituirse por un modelo de lenguaje real en una fase posterior."
            ),
            key_concepts=[
                {"concept": "concepto principal", "weight": 1.0},
                {"concept": "definición", "weight": 0.75},
                {"concept": "explicación", "weight": 0.75},
            ],
            rubric=[
                RubricItem("Identifica correctamente el concepto principal", 1.0),
                RubricItem("Incluye una explicación básica", 0.75),
                RubricItem("Usa terminología adecuada", 0.75),
            ],
            common_mistakes=[
                "Respuesta demasiado vaga",
                "Uso de conceptos incorrectos",
                "Ausencia de explicación",
            ],
            confidence=0.50,
        )
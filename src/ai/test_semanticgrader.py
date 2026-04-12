from ai.mock_generator import MockReferenceGenerator
from ai.semantic_grader import SemanticGrader


def main():
    generator = MockReferenceGenerator()
    grader = SemanticGrader()

    question = "¿Cuál es la función de la mitocondria?"
    reference = generator.generate(
        question=question,
        subject="Biología",
        education_level="ESO/Bachillerato",
        expected_answer_type="respuesta_corta",
    )

    student_answer = "La mitocondria produce energía para la célula mediante ATP."
    result = grader.grade(student_answer, reference)

    print("\n--- CORRECCIÓN ---")
    print("Respuesta alumno:", result["student_answer"])
    print("Nota:", result["score_over_10"])
    print("Conceptos detectados:", result["detected_concepts"])
    print("Conceptos ausentes:", result["missing_concepts"])
    print("Feedback:", result["feedback"])


if __name__ == "__main__":
    main()
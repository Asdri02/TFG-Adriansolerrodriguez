from ai.mock_generator import MockReferenceGenerator


def print_result(result):
    print("\n--- RESULTADO ---")
    print("Pregunta:", result.question)
    print("Materia:", result.subject)
    print("Nivel:", result.education_level)
    print("Tipo:", result.expected_answer_type)
    print("Respuesta ideal:", result.ideal_answer)
    print("Conceptos clave:", result.key_concepts)
    print("Rúbrica:")
    for item in result.rubric:
        print(f"  - {item.criterion}: {item.points} puntos")
    print("Errores frecuentes:", result.common_mistakes)
    print("Confianza:", result.confidence)


def main():
    generator = MockReferenceGenerator()

    question = "¿Cuál es la función de la mitocondria?"
    result = generator.generate(
        question=question,
        subject="Biología",
        education_level="ESO/Bachillerato",
        expected_answer_type="respuesta_corta",
    )
    print_result(result)


if __name__ == "__main__":
    main()
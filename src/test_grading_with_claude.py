"""
test_grading_with_claude.py — Pipeline test that skips OCR.

Demonstrates the wiring between reference_db (Claude API + cache) and
SemanticGrader without depending on Tesseract. OCR is already validated
in test_ocr.py.
"""
from dotenv import load_dotenv
load_dotenv()

from reference_db import get_reference
from ai.semantic_grader import SemanticGrader


def main():
    question = "¿Cuál es la función de la mitocondria?"
    student_answer = "La mitocondria produce energía para la célula mediante ATP."

    print("Generating reference (cache miss = API call, cache hit = instant)...")
    reference = get_reference(
        question,
        subject="Biología",
        education_level="Bachillerato",
    )

    grader = SemanticGrader()
    result = grader.grade(student_answer, reference)

    print("\n--- ENTRADA (sin OCR) ---")
    print("Pregunta:", question)
    print("Respuesta:", student_answer)

    print("\n--- REFERENCIA GENERADA (Claude API + cache) ---")
    print("Respuesta ideal:", reference.ideal_answer)
    print("Conceptos clave:", reference.key_concepts)

    print("\n--- CORRECCIÓN ---")
    print("Nota:", result["score_over_10"])
    print("Conceptos detectados:", result["detected_concepts"])
    print("Conceptos parciales:", result["partial_concepts"])
    print("Conceptos ausentes:", result["missing_concepts"])
    print("Ratio conceptos:", result["concept_ratio"])
    print("Similitud global:", result["similarity_ratio"])
    print("Penalización longitud:", result["length_penalty"])
    print("Feedback:", result["feedback"])


if __name__ == "__main__":
    main()

from dotenv import load_dotenv
load_dotenv()

from pathlib import Path

from ocr.extractor import OCRExtractor
from ocr.parser import ExamTextParser
from reference_db import get_reference
from ai.semantic_grader import SemanticGrader


def main():
    image_path = Path("data/input/exam_open_question.jpg")

    extractor = OCRExtractor(
        tesseract_cmd=None
    )

    raw_text = extractor.extract_text_from_image(
        image_path=str(image_path),
        lang="spa",
    )

    parsed = ExamTextParser.parse_question_and_answer(raw_text)

    question = parsed["question"]
    student_answer = parsed["student_answer"]

    print("Generating reference (cache miss = API call, cache hit = instant)...")
    reference = get_reference(question)

    grader = SemanticGrader()
    result = grader.grade(student_answer, reference)

    print("\n--- OCR ---")
    print("Pregunta detectada:", question)
    print("Respuesta detectada:", student_answer)

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

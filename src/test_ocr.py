from pathlib import Path

from ocr.extractor import OCRExtractor
from ocr.parser import ExamTextParser


def main():
    image_path = Path("data/input/exam_open_question.jpg")

    extractor = OCRExtractor(
        tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    extractor.save_debug_image(
        image_path=str(image_path),
        output_path="data/input/debug_ocr.jpg",
    )

    raw_text = extractor.extract_text_from_image(
        image_path=str(image_path),
        lang="spa",
    )

    parsed = ExamTextParser.parse_question_and_answer(raw_text)

    print("\n--- TEXTO OCR ---")
    print(raw_text)

    print("\n--- PARSEADO ---")
    print("Pregunta:", parsed["question"])
    print("Respuesta alumno:", parsed["student_answer"])


if __name__ == "__main__":
    main()
from typing import Dict


class ExamTextParser:
    @staticmethod
    def clean_text(raw_text: str) -> str:
        text = raw_text.replace("\n\n", "\n").strip()
        return text

    @staticmethod
    def parse_question_and_answer(raw_text: str) -> Dict[str, str]:
        text = ExamTextParser.clean_text(raw_text)

        question = ""
        student_answer = ""

        lower = text.lower()

        q_idx = lower.find("pregunta:")
        r_idx = lower.find("respuesta:")

        if q_idx != -1 and r_idx != -1:
            question = text[q_idx + len("Pregunta:"):r_idx].strip()
            student_answer = text[r_idx + len("Respuesta:"):].strip()
        else:
            lines = [line.strip() for line in text.splitlines() if line.strip()]

            if len(lines) >= 2:
                question = lines[0]
                student_answer = " ".join(lines[1:])
            elif len(lines) == 1:
                question = lines[0]
                student_answer = ""

        return {
            "question": question,
            "student_answer": student_answer,
        }
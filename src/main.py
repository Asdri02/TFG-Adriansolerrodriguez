import cv2
import numpy as np
from pathlib import Path

# --- CONFIG (MVP) ---
# Ejemplo: 10 preguntas, 4 opciones (A-D)
N_QUESTIONS = 10
N_CHOICES = 4

# Solucionario de ejemplo (índice 0=A, 1=B, 2=C, 3=D)
ANSWER_KEY = {
    1: 2,  # Q1 -> C
    2: 0,  # Q2 -> A
    3: 1,
    4: 3,
    5: 2,
    6: 2,
    7: 0,
    8: 1,
    9: 3,
    10: 1,
}

def preprocess(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    # Binarización robusta para distintos fondos
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 31, 7
    )
    # Limpieza ligera
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    return thresh

def find_bubbles(thresh: np.ndarray):
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bubble_cnts = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        ar = w / float(h + 1e-6)

        # Heurística: "burbujas/casillas" de tamaño razonable y forma casi cuadrada/circular
        if area > 150 and 0.7 <= ar <= 1.3 and 12 <= w <= 80 and 12 <= h <= 80:
            bubble_cnts.append(c)

    # Orden por arriba->abajo, luego izquierda->derecha (aprox.)
    bubble_cnts = sorted(bubble_cnts, key=lambda c: cv2.boundingRect(c)[1])
    return bubble_cnts

def group_into_questions(bubble_cnts):
    # Ordena por filas y dentro por x
    # Asume que cada pregunta tiene N_CHOICES "burbujas"
    rows = []
    i = 0
    while i < len(bubble_cnts):
        # toma un bloque candidato y agrupa por proximidad en Y
        x, y, w, h = cv2.boundingRect(bubble_cnts[i])
        same_row = []
        j = i
        while j < len(bubble_cnts):
            x2, y2, w2, h2 = cv2.boundingRect(bubble_cnts[j])
            if abs(y2 - y) < 20:  # tolerancia fila
                same_row.append(bubble_cnts[j])
                j += 1
            else:
                break
        same_row = sorted(same_row, key=lambda c: cv2.boundingRect(c)[0])
        rows.append(same_row)
        i = j
    # Filtra filas que tengan al menos N_CHOICES (a veces hay ruido)
    rows = [r for r in rows if len(r) >= N_CHOICES]
    # Reduce cada fila a N_CHOICES (izquierda->derecha)
    questions = [r[:N_CHOICES] for r in rows[:N_QUESTIONS]]
    return questions

def detect_marked(thresh: np.ndarray, questions):
    marked = {}  # q -> choice_index
    confidences = {}  # q -> fill_ratio
    for q_idx, choices in enumerate(questions, start=1):
        filled = []
        for choice_idx, c in enumerate(choices):
            mask = np.zeros(thresh.shape, dtype="uint8")
            cv2.drawContours(mask, [c], -1, 255, -1)
            # Cuenta pixeles blancos dentro de la burbuja
            total = cv2.countNonZero(mask)
            inside = cv2.countNonZero(cv2.bitwise_and(thresh, thresh, mask=mask))
            ratio = inside / float(total + 1e-6)
            filled.append((ratio, choice_idx))

        filled.sort(reverse=True, key=lambda t: t[0])
        best_ratio, best_choice = filled[0]
        second_ratio = filled[1][0] if len(filled) > 1 else 0.0

        # Regla simple para decidir si está marcada:
        # - suficiente tinta (ratio)
        # - diferencia con la segunda opción (evita ambigüedad)
        if best_ratio > 0.25 and (best_ratio - second_ratio) > 0.05:
            marked[q_idx] = best_choice
            confidences[q_idx] = best_ratio
        else:
            marked[q_idx] = None
            confidences[q_idx] = best_ratio

    return marked, confidences

def grade(marked, answer_key):
    correct = 0
    detail = {}
    for q, correct_choice in answer_key.items():
        student_choice = marked.get(q, None)
        is_correct = (student_choice == correct_choice)
        if is_correct:
            correct += 1
        detail[q] = {
            "student": student_choice,
            "correct": correct_choice,
            "ok": is_correct
        }
    score = correct / max(len(answer_key), 1) * 10.0
    return score, correct, len(answer_key), detail

def main():
    img_path = Path("data/input/exam.jpg")
    image = cv2.imread(str(img_path))
    if image is None:
        raise FileNotFoundError(f"No se pudo leer: {img_path}")

    thresh = preprocess(image)
    bubble_cnts = find_bubbles(thresh)
    questions = group_into_questions(bubble_cnts)
    marked, confidences = detect_marked(thresh, questions)
    score, correct, total, detail = grade(marked, ANSWER_KEY)

    print(f"Nota: {score:.2f}/10 | Aciertos: {correct}/{total}")
    for q in sorted(detail.keys()):
        print(f"Q{q}: student={detail[q]['student']} correct={detail[q]['correct']} ok={detail[q]['ok']} conf={confidences.get(q, 0):.2f}")

if __name__ == "__main__":
    main()

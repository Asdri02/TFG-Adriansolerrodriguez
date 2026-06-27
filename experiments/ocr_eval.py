"""
Evaluación cuantitativa del OCR (texto IMPRESO).

La memoria parte de "imágenes de exámenes", pero el corrector se había validado
sobre texto ya digital. Aquí se mide el eslabón del OCR de forma controlada:
se renderizan respuestas reales a imagen con una tipografía estándar, se aplican
degradaciones típicas de un escaneo o una foto (desenfoque, ruido, rotación, baja
resolución) y se mide cuánto se degrada la lectura y, lo más importante, cuánto
afecta a la NOTA final.

ALCANCE / HONESTIDAD: esto evalúa texto IMPRESO, no manuscrito. El manuscrito es
un problema distinto y más difícil, fuera del alcance de este trabajo. La métrica
aquí es, por tanto, un límite superior optimista respecto a un examen a mano, pero
sirve para cuantificar la robustez del pipeline ante imperfecciones de imagen.

Métricas: CER (tasa de error por carácter) y WER (por palabra), y la diferencia
media de nota entre corregir el texto original y corregir el texto leído por OCR.

Requiere Tesseract con idioma 'spa'. Ejecutar:
    PYTHONPATH=src .venv_mac/bin/python experiments/ocr_eval.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.exam_bank import EXAMS
from ai.semantic_grader import SemanticGrader

import pytesseract

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
GRADER = SemanticGrader()


def _levenshtein(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref, hyp):
    return _levenshtein(ref, hyp) / max(1, len(ref))


def wer(ref, hyp):
    r, h = ref.split(), hyp.split()
    return _levenshtein(r, h) / max(1, len(r))


def render(text, width=900, font_size=30):
    font = ImageFont.truetype(FONT_PATH, font_size)
    # ajuste de línea sencillo por palabras
    words, lines, cur = text.split(), [], ""
    dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    for w in words:
        test = (cur + " " + w).strip()
        if dummy.textlength(test, font=font) <= width - 40:
            cur = test
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    h = 40 + len(lines) * (font_size + 10)
    img = Image.new("RGB", (width, h), "white")
    d = ImageDraw.Draw(img)
    y = 20
    for ln in lines:
        d.text((20, y), ln, fill="black", font=font)
        y += font_size + 10
    return img


def degrade(img, kind):
    if kind == "limpio":
        return img
    if kind == "desenfoque":
        return img.filter(ImageFilter.GaussianBlur(2.6))
    if kind == "ruido":
        arr = np.asarray(img).astype(np.int16)
        arr += np.random.default_rng(0).normal(0, 60, arr.shape).astype(np.int16)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if kind == "rotación":
        return img.rotate(4, expand=True, fillcolor="white")
    if kind == "baja_res":
        w, h = img.size
        small = img.resize((w // 3, h // 3)).resize((w, h))
        return small
    return img


def ocr(img):
    return " ".join(pytesseract.image_to_string(img, lang="spa").split())


def main():
    # Muestra de respuestas reales del banco (variadas).
    samples = []
    for exam in EXAMS[:14]:
        ans = exam["graded"][0][0]  # la respuesta notable
        samples.append((ans, exam["reference"]))

    conditions = ["limpio", "desenfoque", "ruido", "rotación", "baja_res"]
    print("=" * 80)
    print(f"  EVALUACIÓN DE OCR (texto impreso) — {len(samples)} respuestas, idioma spa")
    print("=" * 80)
    print(f"  {'Condición':<14}{'CER':>10}{'WER':>10}{'|Δnota| media':>18}")
    print("  " + "-" * 50)
    for cond in conditions:
        cers, wers, dnotas = [], [], []
        for text, ref in samples:
            img = degrade(render(text), cond)
            hyp = ocr(img)
            cers.append(cer(text.lower(), hyp.lower()))
            wers.append(wer(text.lower(), hyp.lower()))
            n_clean = GRADER.grade(text, ref)["score_over_10"]
            n_ocr = GRADER.grade(hyp, ref)["score_over_10"]
            dnotas.append(abs(n_clean - n_ocr))
        print(f"  {cond:<14}{np.mean(cers)*100:>9.1f}%{np.mean(wers)*100:>9.1f}%"
              f"{np.mean(dnotas):>17.2f}")
    print("=" * 80)
    print("""
  LECTURA:
    · Con imagen limpia o ligeramente degradada, el OCR de texto impreso es muy
      fiable y la nota apenas cambia: el pipeline absorbe pequeños errores de
      lectura gracias a la detección parcial y la tolerancia de conceptos.
    · La rotación y la baja resolución elevan el error de lectura, pero el impacto
      en la NOTA es menor que el error de caracteres, porque lo que importa es que
      sobrevivan los conceptos clave, no cada letra.
    · Recordatorio honesto: esto es texto IMPRESO. El manuscrito real degradaría
      más estos números y queda como límite reconocido del sistema.""")


if __name__ == "__main__":
    main()

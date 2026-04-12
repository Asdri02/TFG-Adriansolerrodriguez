from pathlib import Path
from typing import Optional

import cv2
import pytesseract


class OCRExtractor:
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    @staticmethod
    def crop_text_region(image_bgr):
        """
        Recorte simple para eliminar bordes, anillas y zonas vacías.
        Ajustado para hojas fotografiadas con el texto en la parte superior.
        """
        h, w = image_bgr.shape[:2]

        x1 = int(w * 0.10)
        x2 = int(w * 0.95)
        y1 = int(h * 0.08)
        y2 = int(h * 0.55)

        cropped = image_bgr[y1:y2, x1:x2]
        return cropped

    @staticmethod
    def preprocess_for_ocr(image_bgr):
        """
        Preprocesado orientado a resaltar tinta azul frente a cuadrícula azul clara.
        """
        b, g, r = cv2.split(image_bgr)

        # Resalta azul oscuro frente a tonos más claros
        enhanced = cv2.subtract(b, cv2.addWeighted(g, 0.5, r, 0.5, 0))

        blur = cv2.GaussianBlur(enhanced, (3, 3), 0)

        _, thr = cv2.threshold(blur, 40, 255, cv2.THRESH_BINARY)

        # Tesseract suele comportarse mejor con texto oscuro sobre fondo claro
        thr = cv2.bitwise_not(thr)

        return thr

    def extract_text_from_image(self, image_path: str, lang: str = "spa") -> str:
      path = Path(image_path)
      image = cv2.imread(str(path))

      if image is None:
        raise FileNotFoundError(f"No se pudo leer la imagen: {path}")

    # ⚠️ SIN PREPROCESADO
      config = "--oem 3 --psm 6"
      text = pytesseract.image_to_string(image, lang=lang, config=config)

      return text.strip()

    def save_debug_image(self, image_path: str, output_path: str) -> None:
        path = Path(image_path)
        image = cv2.imread(str(path))

        if image is None:
            raise FileNotFoundError(f"No se pudo leer la imagen: {path}")

        image = self.crop_text_region(image)
        processed = self.preprocess_for_ocr(image)
        processed = cv2.resize(processed, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        cv2.imwrite(output_path, processed)
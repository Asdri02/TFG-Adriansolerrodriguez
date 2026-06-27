"""
Tests de /api/ocr (Tesseract mockeado) y /api/export_docx.
"""

from __future__ import annotations

from pytesseract import TesseractNotFoundError

from web import app as app_module


# ── /api/ocr ─────────────────────────────────────────────────────────────────

def test_ocr_no_imagen_da_400(client):
    resp = client.post(
        "/api/ocr",
        files={"image": ("nota.txt", b"hola", "text/plain")},
    )
    assert resp.status_code == 400


def test_ocr_ok_con_extractor_mockeado(client, monkeypatch):
    monkeypatch.setattr(
        app_module._extractor, "extract_text_from_image",
        lambda path, lang="spa": "Pregunta: ¿Qué es la mitocondria?\nRespuesta: el orgánulo de la energía",
    )
    resp = client.post(
        "/api/ocr",
        files={"image": ("examen.png", b"fakebytes", "image/png")},
        data={"lang": "spa"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "raw_text" in data
    assert "question" in data
    assert "student_answer" in data


def test_ocr_sin_tesseract_da_503(client, monkeypatch):
    def boom(path, lang="spa"):
        raise TesseractNotFoundError()

    monkeypatch.setattr(app_module._extractor, "extract_text_from_image", boom)
    resp = client.post(
        "/api/ocr",
        files={"image": ("examen.png", b"x", "image/png")},
    )
    assert resp.status_code == 503
    assert "Tesseract" in resp.json()["detail"]


# ── /api/export_docx ─────────────────────────────────────────────────────────

def test_export_docx_pregunta_y_respuesta(client):
    resp = client.post("/api/export_docx", json={
        "question": "¿Qué es la mitocondria?",
        "answer": "El orgánulo de la energía.",
        "title": "Examen de Biología",
    })
    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    # un .docx es un zip → empieza por 'PK'
    assert resp.content[:2] == b"PK"
    assert len(resp.content) > 0


def test_export_docx_solo_raw_text(client):
    resp = client.post("/api/export_docx", json={
        "raw_text": "Texto suelto extraído por OCR.",
    })
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"


# ── Endpoints raíz y estáticos ───────────────────────────────────────────────

def test_index_sirve_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]

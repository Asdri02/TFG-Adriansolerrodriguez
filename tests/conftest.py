"""
Configuración compartida de pytest para la batería de tests de la web.

Objetivos de aislamiento:
  - Cada test usa un directorio de datos temporal: ni la BD SQLite real
    (data/calibration.db) ni data/teacher_config.json se tocan nunca.
  - Las llamadas a Claude (anthropic) y a reference_db se mockean: los tests
    no necesitan ANTHROPIC_API_KEY ni red.
  - Tesseract no es necesario salvo en los tests que explícitamente lo mockean.

Para ejecutar:
    PYTHONPATH=src .venv_mac/bin/python -m pytest tests/ -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ── Aislamiento de almacenamiento (BD SQLite + teacher_config.json) ──────────

@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """
    Redirige todas las rutas de persistencia a un tmp_path único por test.

    calibration_db y templates_db comparten el mismo fichero SQLite
    (data/calibration.db) en producción, así que aquí también comparten uno
    temporal — eso ejercita el hecho de que ambas tablas conviven en una sola BD.
    """
    from web import app as app_module
    from web import calibration_db
    from web import gradebook_db
    from web import templates_db

    db_path = tmp_path / "calibration.db"
    gradebook_path = tmp_path / "gradebook.db"
    cfg_path = tmp_path / "teacher_config.json"

    monkeypatch.setattr(calibration_db, "_DB_PATH", db_path)
    monkeypatch.setattr(templates_db, "_DB_PATH", db_path)
    monkeypatch.setattr(gradebook_db, "_DB_PATH", gradebook_path)
    monkeypatch.setattr(app_module, "_TEACHER_CONFIG_PATH", cfg_path)

    yield tmp_path


@pytest.fixture
def client():
    from web.app import app
    return TestClient(app)


# ── Fake de Claude (anthropic) ───────────────────────────────────────────────

class _FakeContent:
    def __init__(self, text: str):
        self.text = text


class _FakeResponse:
    def __init__(self, text: str):
        self.content = [_FakeContent(text)]


class _FakeMessages:
    def __init__(self, controller: "FakeClaude"):
        self._controller = controller

    def create(self, **kwargs):
        self._controller.calls.append(kwargs)
        if self._controller.raise_exc is not None:
            raise self._controller.raise_exc
        return _FakeResponse(self._controller.next_text)


class FakeClaude:
    """
    Controlador inyectable. Sustituye a anthropic.Anthropic: cualquier
    `anthropic.Anthropic()` dentro de un endpoint devuelve este cliente, cuya
    .messages.create() responde con el texto que el test haya configurado.
    """
    def __init__(self):
        self.next_text = "{}"
        self.raise_exc = None
        self.calls = []

    # se instancia como anthropic.Anthropic()
    def __call__(self, *args, **kwargs):
        return self

    @property
    def messages(self):
        return _FakeMessages(self)

    def set_text(self, text: str):
        self.next_text = text

    def set_exception(self, exc: Exception):
        self.raise_exc = exc


@pytest.fixture
def fake_claude(monkeypatch):
    """Parchea anthropic.Anthropic con un fake controlable."""
    import anthropic
    controller = FakeClaude()
    monkeypatch.setattr(anthropic, "Anthropic", controller)
    return controller


@pytest.fixture
def fake_vision(monkeypatch):
    """
    Parchea web.app._call_claude_vision (usado por los endpoints de imagen
    estructurada). Devuelve un controlador con .set_text() / .set_exception().
    """
    from web import app as app_module

    class _VisionController:
        def __init__(self):
            self.next_text = "{}"
            self.raise_exc = None
            self.calls = []

        def __call__(self, image_bytes, media_type, prompt, *, max_tokens=3000):
            self.calls.append({"media_type": media_type, "prompt": prompt})
            if self.raise_exc is not None:
                raise self.raise_exc
            return self.next_text

        def set_text(self, text):
            self.next_text = text

        def set_exception(self, exc):
            self.raise_exc = exc

    ctrl = _VisionController()
    monkeypatch.setattr(app_module, "_call_claude_vision", ctrl)
    return ctrl


# ── Payloads de referencia reutilizables ─────────────────────────────────────

@pytest.fixture
def mitocondria_reference():
    """ReferencePayload válido para la pregunta de la mitocondria."""
    return {
        "question": "¿Qué es la mitocondria?",
        "subject": "Biología",
        "education_level": "Bachillerato",
        "ideal_answer": (
            "La mitocondria es el orgánulo celular responsable de producir "
            "energía en forma de ATP mediante la respiración celular."
        ),
        "key_concepts": [
            {"concept": "orgánulo", "weight": 0.2},
            {"concept": "energía", "weight": 0.3},
            {"concept": "ATP", "weight": 0.3},
            {"concept": "respiración celular", "weight": 0.2},
        ],
        "bonus_terms": [],
    }


def write_teacher_config(monkeypatch_path: Path, cfg: dict) -> None:
    """Helper para escribir un teacher_config directamente (sin pasar por la API)."""
    monkeypatch_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

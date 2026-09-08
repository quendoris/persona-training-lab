from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.panels.inspector_panel import InspectorPanel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_documentation_inspector_describes_source_instead_of_rendered_markdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    panel = InspectorPanel(manager)
    panel.set_context("docs")

    assert panel._status.text() == (
        "The body is read from markdown files under docs/."
    )
    assert "rendered" not in panel._status.text().casefold()

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)

    expected = {
        "ru-RU": "Текст берётся из markdown-файлов в docs/.",
        "es-ES": "El contenido se lee de los archivos Markdown de docs/.",
        "ar": "يُقرأ المحتوى من ملفات Markdown ضمن docs/.",
    }
    for locale, text in expected.items():
        manager.set_locale(locale, persist=False)
        assert panel._status.text() == text

    panel.deleteLater()
    app.processEvents()

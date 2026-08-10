from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.experiments.screen import ExperimentsScreen
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.viewmodels.experiments import ExperimentsViewModel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_experiments_workspace_switches_language_without_rebuilding_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    screen = ExperimentsScreen(ExperimentsViewModel(), manager)
    row_title = screen._rows[0][0]

    assert screen._header_title.text() == "Experiments · No experiments yet"
    assert screen._registry.title_label.text() == "Experiment registry"
    assert row_title.text() == "No experiments yet"
    assert screen._rows[0][2].text() == "empty"

    manager.set_locale("ru-RU", persist=False)

    assert screen._rows[0][0] is row_title
    assert screen._header_title.text() == (
        "Эксперименты · Эксперименты пока не созданы"
    )
    assert screen._registry.title_label.text() == "Реестр экспериментов"
    assert row_title.text() == "Эксперименты пока не созданы"
    assert screen._rows[0][2].text() == "пусто"

    manager.set_locale("en-US", persist=False)

    assert screen._rows[0][0] is row_title
    assert row_title.text() == "No experiments yet"

    screen.deleteLater()
    app.processEvents()

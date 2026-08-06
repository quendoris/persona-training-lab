from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDockWidget, QMenu

from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.shell.status_bar import AppStatusBar


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_shell_titles_and_ready_status_switch_without_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    menu = QMenu()
    dock = QDockWidget()
    status = AppStatusBar(manager)
    manager.bind_title(menu, "shell.panels")
    manager.bind_window_title(dock, "dock.inspector")

    assert menu.title() == "Panels"
    assert dock.windowTitle() == "Inspector"
    assert status.currentMessage() == "Ready"

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    manager.set_locale("ru-RU", persist=False)

    assert menu.title() == "Панели"
    assert dock.windowTitle() == "Инспектор"
    assert status.currentMessage() == "Готово"

    menu.deleteLater()
    dock.deleteLater()
    status.deleteLater()
    app.processEvents()

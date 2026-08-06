from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QDockWidget, QLabel, QMainWindow

from persona_training_lab.ui.shell.window_state import WindowStateStore


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _window() -> QMainWindow:
    window = QMainWindow()
    dock = QDockWidget("Инспектор", window)
    dock.setObjectName("Инспектор")
    dock.setWidget(QLabel("context"))
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    return window


def test_window_state_round_trip_preserves_shell_and_workspace(tmp_path) -> None:
    app = _app()
    settings = QSettings(
        str(tmp_path / "shell.ini"),
        QSettings.Format.IniFormat,
    )
    store = WindowStateStore(settings)

    original = _window()
    original.setGeometry(40, 60, 980, 680)
    assert store.save(original, "agents")

    restored_window = _window()
    result = store.restore(restored_window)

    assert result.geometry_restored
    assert result.docks_restored
    assert result.workspace_key == "agents"
    assert result.any_restored
    assert restored_window.size() == original.size()

    original.deleteLater()
    restored_window.deleteLater()
    app.processEvents()


def test_invalid_or_missing_state_is_ignored_without_raising(tmp_path) -> None:
    app = _app()
    settings = QSettings(
        str(tmp_path / "broken.ini"),
        QSettings.Format.IniFormat,
    )
    settings.setValue(WindowStateStore.GEOMETRY_KEY, "not-a-byte-array")
    settings.setValue(WindowStateStore.DOCK_STATE_KEY, "also-invalid")
    settings.setValue(WindowStateStore.WORKSPACE_KEY, "datasets")
    settings.sync()

    store = WindowStateStore(settings)
    window = _window()
    result = store.restore(window)

    assert not result.geometry_restored
    assert not result.docks_restored
    assert result.workspace_key == "datasets"
    assert not result.any_restored

    store.clear()
    assert settings.value(WindowStateStore.GEOMETRY_KEY) is None
    assert settings.value(WindowStateStore.DOCK_STATE_KEY) is None
    assert settings.value(WindowStateStore.WORKSPACE_KEY) is None

    window.deleteLater()
    app.processEvents()

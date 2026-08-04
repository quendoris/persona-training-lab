from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.keybindings.screen import KeyBindingsScreen


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _screen(tmp_path) -> tuple[QApplication, KeyBindingManager, KeyBindingsScreen]:
    app = _app()
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    screen = KeyBindingsScreen(manager)
    return app, manager, screen


def test_direct_capture_is_deferred_past_the_initiating_click(tmp_path) -> None:
    app, _manager, screen = _screen(tmp_path)

    screen._schedule_capture("keyboard", "history_toggle")

    assert screen._capture_kind is None
    assert screen._capture_binding_id is None
    app.processEvents()
    assert screen._capture_kind == "keyboard"
    assert screen._capture_binding_id == "history_toggle"
    assert screen._sequence_chips["history_toggle"]._capturing is True

    screen._cancel_capture()
    screen.deleteLater()
    app.processEvents()


def test_direct_keyboard_capture_applies_valid_sequence(tmp_path) -> None:
    app, manager, screen = _screen(tmp_path)
    screen._start_capture("keyboard", "history_toggle")
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Y,
        Qt.KeyboardModifier.ControlModifier,
        "y",
    )

    handled = screen.eventFilter(screen, event)

    assert handled is True
    assert manager.sequence("history_toggle") == "Ctrl+Y"
    assert screen._capture_kind is None
    assert screen._sequence_chips["history_toggle"]._capturing is False

    screen.deleteLater()
    app.processEvents()


def test_direct_conflict_stays_visible_but_not_active(tmp_path) -> None:
    app, manager, screen = _screen(tmp_path)
    screen._start_capture("keyboard", "delete_branch")
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Z,
        Qt.KeyboardModifier.ControlModifier,
        "z",
    )

    handled = screen.eventFilter(screen, event)

    assert handled is True
    assert screen._draft.sequence("delete_branch") == "Ctrl+Z"
    assert manager.sequence("delete_branch") == "Del"
    assert set(screen._draft.keyboard_conflicts()) == {
        "delete_branch",
        "history_toggle",
    }
    assert screen._keyboard_cards["delete_branch"]._has_conflict is True
    assert screen._keyboard_cards["history_toggle"]._has_conflict is True

    screen.deleteLater()
    app.processEvents()


def test_escape_cancels_direct_capture_without_changing_binding(tmp_path) -> None:
    app, manager, screen = _screen(tmp_path)
    original = manager.sequence("undo_only")
    screen._start_capture("keyboard", "undo_only")
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )

    handled = screen.eventFilter(screen, event)

    assert handled is True
    assert manager.sequence("undo_only") == original
    assert screen._capture_kind is None
    assert screen._sequence_chips["undo_only"]._capturing is False

    screen.deleteLater()
    app.processEvents()


def test_capture_chip_pulse_survives_live_theme_change(tmp_path) -> None:
    app, _manager, screen = _screen(tmp_path)
    chip = screen._sequence_chips["history_toggle"]
    chip.resize(180, 34)
    chip.set_capturing(True)

    app.setProperty("ptl_theme_name", "velvet")
    app.setProperty("ptl_accent_name", "cyan")
    first = chip.grab()
    app.setProperty("ptl_accent_name", "magenta")
    chip._toggle_pulse()
    second = chip.grab()

    assert first.isNull() is False
    assert second.isNull() is False
    assert chip._pulse_timer.isActive() is True

    chip.set_capturing(False)
    screen.deleteLater()
    app.processEvents()

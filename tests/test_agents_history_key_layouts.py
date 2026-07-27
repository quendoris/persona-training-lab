from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


def _press(key: int, text: str = "", modifiers=Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text)


def test_history_z_key_is_recognised_in_latin_layout() -> None:
    event = _press(Qt.Key.Key_Z, "z", Qt.KeyboardModifier.ControlModifier)

    assert AgentsScreen._history_key_name(event) == "z"


def test_history_z_key_is_recognised_in_russian_layout() -> None:
    event = _press(ord("Я"), "я", Qt.KeyboardModifier.ControlModifier)

    assert AgentsScreen._history_key_name(event) == "z"


def test_history_z_key_accepts_ctrl_z_control_character() -> None:
    event = _press(Qt.Key.Key_unknown, "\x1a", Qt.KeyboardModifier.ControlModifier)

    assert AgentsScreen._history_key_name(event) == "z"


def test_history_sequences_are_removed_from_qt_shortcut_routing() -> None:
    assert AgentsScreen._sequence_is_history(QKeySequence("Ctrl+Z")) is True
    assert AgentsScreen._sequence_is_history(QKeySequence("Ctrl+Shift+Z")) is True
    assert AgentsScreen._sequence_is_history(QKeySequence("Del")) is False

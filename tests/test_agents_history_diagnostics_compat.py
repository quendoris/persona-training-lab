from __future__ import annotations

from PySide6.QtCore import QEvent, Qt

from persona_training_lab.ui.agents.screen_history_diagnostics_compat import AgentsScreen


def test_qt_numeric_value_accepts_keyboard_modifier_flags() -> None:
    combined = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier

    assert AgentsScreen._qt_numeric_value(Qt.KeyboardModifier.ControlModifier) == int(
        Qt.KeyboardModifier.ControlModifier.value
    )
    assert AgentsScreen._qt_numeric_value(combined) == int(combined.value)


def test_qt_numeric_value_accepts_key_and_event_enums() -> None:
    assert AgentsScreen._qt_numeric_value(Qt.Key.Key_Z) == int(Qt.Key.Key_Z.value)
    assert AgentsScreen._qt_numeric_value(QEvent.Type.KeyPress) == int(QEvent.Type.KeyPress.value)
    assert AgentsScreen._event_type_name(QEvent.Type.KeyPress) == "KeyPress"

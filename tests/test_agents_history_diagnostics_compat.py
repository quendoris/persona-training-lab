from __future__ import annotations

import importlib

from PySide6.QtCore import QEvent, Qt

import persona_training_lab.ui.agents as agents_package
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


def test_legacy_history_diagnostics_import_routes_to_compatible_screen() -> None:
    legacy_module = importlib.import_module("persona_training_lab.ui.agents.screen_history_diagnostics")
    compatible_module = importlib.import_module("persona_training_lab.ui.agents.screen_history_diagnostics_compat")

    assert legacy_module is compatible_module
    assert legacy_module.AgentsScreen is agents_package.AgentsScreen

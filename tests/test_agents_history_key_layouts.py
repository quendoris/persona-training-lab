from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence

from persona_training_lab.ui.agents.history_shortcut_routing import (
    HistoryShortcutRouting,
)
from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


def _press(key: int, text: str = "", modifiers=Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text)


def _native_key_event(
    event_type: QEvent.Type,
    *,
    scan_code: int,
    modifiers=Qt.KeyboardModifier.NoModifier,
) -> QKeyEvent:
    return QKeyEvent(
        event_type,
        Qt.Key.Key_unknown,
        modifiers,
        scan_code,
        0,
        0,
        "",
    )


def test_history_z_key_is_recognised_in_latin_layout() -> None:
    event = _press(Qt.Key.Key_Z, "z", Qt.KeyboardModifier.ControlModifier)

    assert AgentsScreen._history_key_name(event) == "z"


def test_history_z_key_is_recognised_in_russian_layout() -> None:
    event = _press(ord("Я"), "я", Qt.KeyboardModifier.ControlModifier)

    assert AgentsScreen._history_key_name(event) == "z"


def test_history_z_key_accepts_ctrl_z_control_character() -> None:
    event = _press(Qt.Key.Key_unknown, "\x1a", Qt.KeyboardModifier.ControlModifier)

    assert AgentsScreen._history_key_name(event) == "z"


def test_xkb_shift_consumed_by_layout_switch_is_recognised_from_scan_code() -> None:
    event = _native_key_event(
        QEvent.Type.KeyPress,
        scan_code=50,
        modifiers=Qt.KeyboardModifier.ControlModifier,
    )

    assert event.key() == Qt.Key.Key_unknown
    assert event.text() == ""
    assert AgentsScreen._history_key_name(event) == "shift"


def test_physical_shift_scan_codes_cover_evdev_and_xkb_sides() -> None:
    for scan_code in (42, 50, 54, 62):
        press = _native_key_event(QEvent.Type.KeyPress, scan_code=scan_code)
        release = _native_key_event(QEvent.Type.KeyRelease, scan_code=scan_code)

        assert AgentsScreen._history_key_name(press) == "shift"
        assert AgentsScreen._history_key_name(release) == "shift"


def test_history_sequences_are_removed_from_qt_shortcut_routing() -> None:
    routing = HistoryShortcutRouting()

    assert routing.sequence_is_history(QKeySequence("Ctrl+Z")) is True
    assert routing.sequence_is_history(QKeySequence("Ctrl+Shift+Z")) is True
    assert routing.sequence_is_history(QKeySequence("Del")) is False

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.history_key_resolver import HistoryKeyResolver


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


def test_latin_z_resolves_to_history_key() -> None:
    event = _press(Qt.Key.Key_Z, "z", Qt.KeyboardModifier.ControlModifier)

    assert HistoryKeyResolver.key_name(event) == "z"


def test_russian_layout_z_resolves_from_ya_character() -> None:
    event = _press(ord("Я"), "я", Qt.KeyboardModifier.ControlModifier)

    assert HistoryKeyResolver.key_name(event) == "z"


def test_ctrl_z_control_character_resolves_without_logical_key() -> None:
    event = _press(Qt.Key.Key_unknown, "\x1a", Qt.KeyboardModifier.ControlModifier)

    assert HistoryKeyResolver.key_name(event) == "z"


def test_xkb_consumed_shift_resolves_from_physical_scan_code() -> None:
    event = _native_key_event(
        QEvent.Type.KeyPress,
        scan_code=50,
        modifiers=Qt.KeyboardModifier.ControlModifier,
    )

    assert event.key() == Qt.Key.Key_unknown
    assert event.text() == ""
    assert HistoryKeyResolver.key_name(event) == "shift"


def test_physical_shift_scan_codes_cover_evdev_and_xkb_sides() -> None:
    for scan_code in HistoryKeyResolver.PHYSICAL_SHIFT_SCAN_CODES:
        press = _native_key_event(QEvent.Type.KeyPress, scan_code=scan_code)
        release = _native_key_event(QEvent.Type.KeyRelease, scan_code=scan_code)

        assert HistoryKeyResolver.key_name(press) == "shift"
        assert HistoryKeyResolver.key_name(release) == "shift"


def test_physical_z_scan_codes_cover_evdev_and_xkb_forms() -> None:
    for scan_code in HistoryKeyResolver.PHYSICAL_Z_SCAN_CODES:
        event = _native_key_event(QEvent.Type.KeyPress, scan_code=scan_code)

        assert HistoryKeyResolver.key_name(event) == "z"

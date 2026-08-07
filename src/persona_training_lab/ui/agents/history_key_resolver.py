from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent


class HistoryKeyResolver:
    """Resolve portable history key names from logical and physical Qt events."""

    # Linux evdev codes and their X11/XKB (+8) equivalents.
    PHYSICAL_SHIFT_SCAN_CODES = frozenset({42, 50, 54, 62})
    PHYSICAL_Z_SCAN_CODES = frozenset({44, 52})

    @classmethod
    def key_name(cls, event: QKeyEvent) -> str | None:
        key = event.key()
        scan_code = int(event.nativeScanCode())
        if key == Qt.Key.Key_Control:
            return "control"
        if key == Qt.Key.Key_Shift or scan_code in cls.PHYSICAL_SHIFT_SCAN_CODES:
            return "shift"
        if key == Qt.Key.Key_Z:
            return "z"
        text = event.text().casefold()
        if text in {"z", "я", "\x1a"}:
            return "z"
        if key in {ord("Я"), ord("я")}:
            return "z"
        if scan_code in cls.PHYSICAL_Z_SCAN_CODES:
            return "z"
        return None

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication


@dataclass(frozen=True, slots=True)
class HistoryModifierSnapshot:
    """Normalized history-relevant keyboard modifier state."""

    control: bool = False
    shift: bool = False
    alt: bool = False
    meta: bool = False

    @classmethod
    def from_qt(cls, modifiers: Qt.KeyboardModifier) -> "HistoryModifierSnapshot":
        return cls(
            control=bool(modifiers & Qt.KeyboardModifier.ControlModifier),
            shift=bool(modifiers & Qt.KeyboardModifier.ShiftModifier),
            alt=bool(modifiers & Qt.KeyboardModifier.AltModifier),
            meta=bool(modifiers & Qt.KeyboardModifier.MetaModifier),
        )

    @classmethod
    def current(cls) -> "HistoryModifierSnapshot":
        return cls.from_qt(QGuiApplication.queryKeyboardModifiers())

    @property
    def has_extra_history_modifiers(self) -> bool:
        return self.alt or self.meta

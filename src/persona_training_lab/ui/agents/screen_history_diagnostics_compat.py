from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.screen_history_diagnostics import AgentsScreen as _DiagnosticsAgentsScreen
from persona_training_lab.ui.agents.screen_history_keyguard_sticky import AgentsScreen as _StickyHistoryAgentsScreen


class AgentsScreen(_DiagnosticsAgentsScreen):
    """Log history key events without assuming Qt enums inherit from int."""

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if isinstance(event, QKeyEvent):
            key_name = self._history_key_name(event)
            modifiers = event.modifiers()
            relevant = key_name is not None or bool(modifiers & Qt.KeyboardModifier.ControlModifier)
            if relevant and event.type() in (
                QEvent.Type.KeyPress,
                QEvent.Type.KeyRelease,
                QEvent.Type.ShortcutOverride,
            ):
                self._debug_log(
                    "KEY_EVENT",
                    event=self._event_type_name(event.type()),
                    key_name=key_name or "other",
                    key=self._qt_numeric_value(event.key()),
                    text=repr(event.text()),
                    scan=self._qt_numeric_value(event.nativeScanCode()),
                    modifiers=self._qt_numeric_value(modifiers),
                    repeat=event.isAutoRepeat(),
                    watched=type(watched).__name__,
                    state=self._history_state_text(),
                    queried=self._queried_modifier_text(),
                )
        elif self._KEYBOARD_LAYOUT_CHANGE is not None and event.type() == self._KEYBOARD_LAYOUT_CHANGE:
            self._debug_log("KEYBOARD_LAYOUT_CHANGE_EVENT", watched=type(watched).__name__)
            self._note_input_locale_change("event")

        # Skip the diagnostic parent's eventFilter because it contains the legacy
        # direct int(KeyboardModifier) conversion. Continue with the actual keyguard.
        return _StickyHistoryAgentsScreen.eventFilter(self, watched, event)

    @staticmethod
    def _qt_numeric_value(value: Any) -> int | str:
        raw_value = getattr(value, "value", value)
        try:
            return int(raw_value)
        except (TypeError, ValueError, OverflowError):
            return repr(value)

    @classmethod
    def _event_type_name(cls, event_type: QEvent.Type) -> str:
        name = getattr(event_type, "name", None)
        if name:
            return str(name)
        return str(cls._qt_numeric_value(event_type))

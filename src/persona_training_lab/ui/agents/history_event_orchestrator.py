from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QEvent
from PySide6.QtGui import QKeyEvent


@dataclass(slots=True)
class HistoryEventOrchestrator:
    """Route history-related Qt events without owning screen behaviour."""

    stop_modifier_poll: Callable[[], None]
    reset_history_gesture: Callable[[], None]
    sync_modifier_polling: Callable[[], None]
    handle_keyboard_layout_change: Callable[[], None]
    history_keys_are_active: Callable[[], bool]
    history_key_name: Callable[[QKeyEvent], str | None]
    claims_history_override: Callable[[QKeyEvent, str | None], bool]
    block_graph_flip: Callable[[], None]
    handle_history_key_press: Callable[[QKeyEvent, str], bool]
    handle_history_key_release: Callable[[str], bool]
    keyboard_layout_change: QEvent.Type | None

    def route(self, *, watched_is_owner: bool, event: QEvent) -> bool | None:
        """Return a filter result, or ``None`` when the caller should delegate."""

        event_type = event.type()

        # An internal dialog can deactivate the owner window while the
        # application remains active. Stop polling, but preserve the gesture.
        if event_type == QEvent.Type.WindowDeactivate:
            self.stop_modifier_poll()
            return False

        if event_type == QEvent.Type.ApplicationDeactivate:
            self.stop_modifier_poll()
            self.reset_history_gesture()
            return None

        if event_type in (QEvent.Type.ApplicationActivate, QEvent.Type.WindowActivate):
            self.sync_modifier_polling()
        elif watched_is_owner and event_type == QEvent.Type.Hide:
            self.stop_modifier_poll()
        elif watched_is_owner and event_type == QEvent.Type.Show:
            self.sync_modifier_polling()

        if self.keyboard_layout_change is not None and event_type == self.keyboard_layout_change:
            self.handle_keyboard_layout_change()
            return None

        if not isinstance(event, QKeyEvent) or not self.history_keys_are_active():
            return None

        key_name = self.history_key_name(event)

        if event_type == QEvent.Type.ShortcutOverride:
            if self.claims_history_override(event, key_name):
                self.block_graph_flip()
                event.accept()
                return True
            return None

        if event_type not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease) or key_name is None:
            return None

        if event_type == QEvent.Type.KeyPress:
            if self.handle_history_key_press(event, key_name):
                event.accept()
                return True
            return None

        if self.handle_history_key_release(key_name):
            event.accept()
            return True
        return None

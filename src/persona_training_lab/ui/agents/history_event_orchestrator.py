from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PySide6.QtCore import QEvent
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.history_input_environment import (
    HistoryInputEnvironmentSnapshot,
)


class HistoryEventPort(Protocol):
    def _stop_modifier_polling(self) -> None: ...

    def _reset_history_gesture(self) -> None: ...

    def _sync_modifier_polling(
        self,
        environment: HistoryInputEnvironmentSnapshot | None = None,
    ) -> None: ...

    def _handle_keyboard_layout_change(
        self,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> None: ...

    def _history_key_name(self, event: QKeyEvent) -> str | None: ...

    def _claims_history_override(
        self,
        event: QKeyEvent,
        key_name: str | None,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> bool: ...

    def _block_graph_flip(self) -> None: ...

    def _handle_history_key_press(
        self,
        event: QKeyEvent,
        key_name: str,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> bool: ...

    def _handle_history_key_release(self, key_name: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class HistoryEventOrchestrator:
    """Route one Qt event from one coherent input-environment observation."""

    keyboard_layout_change: QEvent.Type | None

    def route(
        self,
        port: HistoryEventPort,
        *,
        watched_is_owner: bool,
        event: QEvent,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> bool | None:
        """Return a filter result, or ``None`` when the caller should delegate."""

        event_type = event.type()

        # An internal dialog can deactivate the owner window while the
        # application remains active. Stop polling, but preserve the gesture.
        if event_type == QEvent.Type.WindowDeactivate:
            port._stop_modifier_polling()
            return False

        if event_type == QEvent.Type.ApplicationDeactivate:
            port._stop_modifier_polling()
            port._reset_history_gesture()
            return None

        if event_type in (QEvent.Type.ApplicationActivate, QEvent.Type.WindowActivate):
            port._sync_modifier_polling(environment)
        elif watched_is_owner and event_type == QEvent.Type.Hide:
            port._stop_modifier_polling()
        elif watched_is_owner and event_type == QEvent.Type.Show:
            port._sync_modifier_polling(environment)

        if self.keyboard_layout_change is not None and event_type == self.keyboard_layout_change:
            port._handle_keyboard_layout_change(environment)
            return None

        if not isinstance(event, QKeyEvent) or not environment.input_active:
            return None

        key_name = port._history_key_name(event)

        if event_type == QEvent.Type.ShortcutOverride:
            if port._claims_history_override(event, key_name, environment):
                port._block_graph_flip()
                event.accept()
                return True
            return None

        if event_type not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease) or key_name is None:
            return None

        if event_type == QEvent.Type.KeyPress:
            if port._handle_history_key_press(event, key_name, environment):
                event.accept()
                return True
            return None

        if port._handle_history_key_release(key_name):
            event.accept()
            return True
        return None

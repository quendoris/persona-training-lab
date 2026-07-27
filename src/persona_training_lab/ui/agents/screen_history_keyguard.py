from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QPushButton

from persona_training_lab.ui.agents.history_key_state import HISTORY_TOGGLE, HISTORY_UNDO, HistoryKeyState
from persona_training_lab.ui.agents.screen_stateful_fixed import AgentsScreen as _StatefulFixedAgentsScreen


class AgentsScreen(_StatefulFixedAgentsScreen):
    """Own history key gestures before Qt can route them to another action."""

    _HISTORY_BINDING_IDS = ("history_toggle", "undo_only")
    _REPEAT_DELAY_MS = 330
    _REPEAT_INTERVAL_MS = 85
    _FLIP_GUARD_SECONDS = 0.35

    def __init__(self, view_model) -> None:
        super().__init__(view_model)

        # Ctrl+Z and Ctrl+Shift+Z are handled as one live key gesture below.
        # Leaving QShortcut instances enabled would let Qt's Undo/Redo matching
        # compete with modifier changes and auto-repeat.
        for binding_id in self._HISTORY_BINDING_IDS:
            shortcut = getattr(self, "_shortcuts", {}).get(binding_id)
            if shortcut is not None:
                shortcut.setEnabled(False)

        self._history_keys = HistoryKeyState()
        self._flip_blocked_until = 0.0

        self._undo_repeat_delay = QTimer(self)
        self._undo_repeat_delay.setSingleShot(True)
        self._undo_repeat_delay.setInterval(self._REPEAT_DELAY_MS)
        self._undo_repeat_delay.timeout.connect(self._start_undo_repeat)

        self._undo_repeat = QTimer(self)
        self._undo_repeat.setInterval(self._REPEAT_INTERVAL_MS)
        self._undo_repeat.timeout.connect(self._repeat_undo_history)

        # The flip control must never be keyboard-activated by a leaked history
        # event. It remains fully clickable with the mouse.
        for button in self.findChildren(QPushButton):
            if button.text().replace("&", "") == "Отразить":
                button.setShortcut(QKeySequence())
                button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                button.setAutoDefault(False)
                button.setDefault(False)

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        event_type = event.type()
        if event_type in (QEvent.Type.ApplicationDeactivate, QEvent.Type.WindowDeactivate):
            self._reset_history_gesture()
            return super().eventFilter(watched, event)

        if not isinstance(event, QKeyEvent) or not self._history_keys_are_active():
            return super().eventFilter(watched, event)

        if event_type == QEvent.Type.ShortcutOverride:
            if self._claims_history_override(event):
                self._block_graph_flip()
                event.accept()
                return True
            return super().eventFilter(watched, event)

        if event_type not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            return super().eventFilter(watched, event)

        key_name = self._history_key_name(event.key())
        if key_name is None:
            return super().eventFilter(watched, event)

        if event_type == QEvent.Type.KeyPress:
            modifiers = event.modifiers()
            # Prime modifiers that may have been held before this widget gained
            # focus, but do not prime the key currently generating the event.
            self._history_keys.prime_modifiers(
                control=key_name != "control" and bool(modifiers & Qt.KeyboardModifier.ControlModifier),
                shift=key_name != "shift" and bool(modifiers & Qt.KeyboardModifier.ShiftModifier),
            )
            actions = self._history_keys.press(key_name)
            claimed = bool(actions) or self._history_keys.history_gesture_active
            if key_name == "shift" and self._history_keys.control_down and self._history_keys.z_down:
                claimed = True
            if key_name == "control" and self._history_keys.z_down:
                claimed = True
            if not claimed:
                return super().eventFilter(watched, event)

            self._block_graph_flip()
            for action in actions:
                self._dispatch_history_key_action(action)
            event.accept()
            return True

        claimed = self._history_keys.release(key_name)
        if not claimed:
            return super().eventFilter(watched, event)
        self._stop_undo_repeat()
        self._block_graph_flip()
        event.accept()
        return True

    def _dispatch_history_key_action(self, action: str) -> None:
        if action == HISTORY_TOGGLE:
            self._stop_undo_repeat()
            self._toggle_last_history_action()
            return
        if action == HISTORY_UNDO:
            self._undo_history_only()
            self._arm_undo_repeat()

    def _arm_undo_repeat(self) -> None:
        self._undo_repeat.stop()
        if self._history_keys.undo_repeat_active and self._state.can_undo():
            self._undo_repeat_delay.start()

    def _start_undo_repeat(self) -> None:
        if self._history_keys.undo_repeat_active and self._state.can_undo():
            self._undo_repeat.start()

    def _repeat_undo_history(self) -> None:
        if not self._history_keys.undo_repeat_active or not self._state.can_undo():
            self._stop_undo_repeat()
            return
        self._block_graph_flip()
        self._undo_history_only()

    def _stop_undo_repeat(self) -> None:
        self._undo_repeat_delay.stop()
        self._undo_repeat.stop()

    def _reset_history_gesture(self) -> None:
        self._stop_undo_repeat()
        self._history_keys.reset()
        self._block_graph_flip()

    def _claims_history_override(self, event: QKeyEvent) -> bool:
        key_name = self._history_key_name(event.key())
        if key_name is None:
            return False
        modifiers = event.modifiers()
        control = self._history_keys.control_down or bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        if key_name == "z" and control:
            return True
        if key_name == "shift" and self._history_keys.control_down and self._history_keys.z_down:
            return True
        if key_name == "control" and self._history_keys.z_down:
            return True
        return self._history_keys.mode is not None and key_name in {"control", "shift", "z"}

    def _toggle_graph_flip(self) -> None:
        # A queued shortcut/button activation from the same key gesture must not
        # mutate graph orientation after the history handler already consumed it.
        if self._graph_flip_is_blocked():
            return
        super()._toggle_graph_flip()

    def _block_graph_flip(self) -> None:
        self._flip_blocked_until = max(
            self._flip_blocked_until,
            monotonic() + self._FLIP_GUARD_SECONDS,
        )

    def _graph_flip_is_blocked(self) -> bool:
        return self._history_keys.mode is not None or monotonic() < self._flip_blocked_until

    @staticmethod
    def _history_key_name(key: int) -> str | None:
        if key == Qt.Key.Key_Control:
            return "control"
        if key == Qt.Key.Key_Shift:
            return "shift"
        if key == Qt.Key.Key_Z:
            return "z"
        return None

    def _history_keys_are_active(self) -> bool:
        app = QApplication.instance()
        if app is None or not self.isVisible() or not self.window().isActiveWindow():
            return False
        if app.activeModalWidget() is not None:
            return False
        focus = app.focusWidget()
        return focus is None or focus.window() is self.window()

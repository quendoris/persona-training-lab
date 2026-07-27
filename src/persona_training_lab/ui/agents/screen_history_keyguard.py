from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QAction, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QPushButton

from persona_training_lab.ui.agents.history_key_state import HistoryKeyState
from persona_training_lab.ui.agents.screen_stateful_fixed import AgentsScreen as _StatefulFixedAgentsScreen


class AgentsScreen(_StatefulFixedAgentsScreen):
    """Own history key gestures before Qt can route them to another action."""

    _HISTORY_BINDING_IDS = ("history_toggle", "undo_only")
    _HISTORY_SEQUENCES = frozenset({"ctrl+z", "ctrl+shift+z"})
    # Qt reports an evdev scan code under Wayland and an XKB scan code under X11.
    # Both values below refer to the physical Latin Z key on a standard keyboard.
    _PHYSICAL_Z_SCAN_CODES = frozenset({44, 52})
    _REPEAT_DELAY_MS = 330
    _REPEAT_INTERVAL_MS = 85
    _FLIP_GUARD_SECONDS = 0.35

    def __init__(self, view_model) -> None:
        super().__init__(view_model)

        self._history_keys = HistoryKeyState()
        self._flip_blocked_until = 0.0

        self._undo_repeat_delay = QTimer(self)
        self._undo_repeat_delay.setSingleShot(True)
        self._undo_repeat_delay.setInterval(self._REPEAT_DELAY_MS)
        self._undo_repeat_delay.timeout.connect(self._start_undo_repeat)

        self._undo_repeat = QTimer(self)
        self._undo_repeat.setInterval(self._REPEAT_INTERVAL_MS)
        self._undo_repeat.timeout.connect(self._repeat_undo_history)

        self._disable_conflicting_history_bindings()
        QTimer.singleShot(0, self._disable_conflicting_history_bindings)

        # The flip control remains mouse-clickable, but cannot receive a leaked
        # keyboard activation from a history chord.
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

        key_name = self._history_key_name(event)

        if event_type == QEvent.Type.ShortcutOverride:
            if self._claims_history_override(event, key_name):
                self._block_graph_flip()
                event.accept()
                return True
            return super().eventFilter(watched, event)

        if event_type not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease) or key_name is None:
            return super().eventFilter(watched, event)

        if event_type == QEvent.Type.KeyPress:
            if self._handle_history_key_press(event, key_name):
                event.accept()
                return True
            return super().eventFilter(watched, event)

        if self._handle_history_key_release(key_name):
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def _handle_history_key_press(self, event: QKeyEvent, key_name: str) -> bool:
        control, shift = self._effective_modifiers(event)

        if key_name == "control":
            self._history_keys.control_down = True
            return self._history_keys.z_down

        if key_name == "shift":
            self._history_keys.shift_down = True
            if not (self._history_keys.control_down and self._history_keys.z_down):
                return False
            self._block_graph_flip()
            if self._history_keys.mode != "undo_only" and not event.isAutoRepeat():
                self._history_keys.mode = "undo_only"
                self._undo_history_only()
                self._arm_undo_repeat()
            return True

        if key_name != "z" or not control:
            return False

        self._history_keys.control_down = True
        self._history_keys.shift_down = shift
        self._history_keys.z_down = True
        self._block_graph_flip()

        if shift:
            if self._history_keys.mode != "undo_only":
                self._history_keys.mode = "undo_only"
                if not event.isAutoRepeat():
                    self._undo_history_only()
                    self._arm_undo_repeat()
            return True

        if self._history_keys.mode is None:
            self._history_keys.mode = "toggle"
            if not event.isAutoRepeat():
                self._toggle_last_history_action()
        return True

    def _handle_history_key_release(self, key_name: str) -> bool:
        claimed = self._history_keys.history_gesture_active or self._history_keys.mode is not None
        if key_name == "control":
            self._history_keys.control_down = False
            self._history_keys.mode = None
        elif key_name == "shift":
            self._history_keys.shift_down = False
            if self._history_keys.mode == "undo_only":
                self._history_keys.mode = "spent"
        elif key_name == "z":
            self._history_keys.z_down = False
            self._history_keys.mode = None
        else:
            return False

        if claimed:
            self._stop_undo_repeat()
            self._block_graph_flip()
        return claimed

    def _effective_modifiers(self, event: QKeyEvent) -> tuple[bool, bool]:
        app = QApplication.instance()
        live_modifiers = app.keyboardModifiers() if app is not None else Qt.KeyboardModifier.NoModifier
        modifiers = event.modifiers() | live_modifiers
        control = self._history_keys.control_down or bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        shift = self._history_keys.shift_down or bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        return control, shift

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

    def _claims_history_override(self, event: QKeyEvent, key_name: str | None) -> bool:
        if key_name is None:
            return False
        control, _shift = self._effective_modifiers(event)
        if key_name == "z" and control:
            return True
        if key_name == "shift" and self._history_keys.control_down and self._history_keys.z_down:
            return True
        if key_name == "control" and self._history_keys.z_down:
            return True
        return self._history_keys.mode is not None and key_name in {"control", "shift", "z"}

    def _disable_conflicting_history_bindings(self) -> None:
        # Disable the known shortcuts created by the inherited screen first.
        for binding_id in self._HISTORY_BINDING_IDS:
            shortcut = getattr(self, "_shortcuts", {}).get(binding_id)
            if shortcut is not None:
                shortcut.setEnabled(False)
                shortcut.setKey(QKeySequence())

        # Then remove any duplicate shortcuts/actions added elsewhere in the
        # screen tree. This leaves the raw event filter as the sole owner.
        for shortcut in self.findChildren(QShortcut):
            if self._sequence_is_history(shortcut.key()):
                shortcut.setEnabled(False)
                shortcut.setKey(QKeySequence())
        for action in self.findChildren(QAction):
            remaining = [sequence for sequence in action.shortcuts() if not self._sequence_is_history(sequence)]
            if len(remaining) != len(action.shortcuts()):
                action.setShortcuts(remaining)

    @classmethod
    def _sequence_is_history(cls, sequence: QKeySequence) -> bool:
        text = sequence.toString(QKeySequence.SequenceFormat.PortableText)
        return text.replace(" ", "").casefold() in cls._HISTORY_SEQUENCES

    def _toggle_graph_flip(self) -> None:
        if self._graph_flip_is_blocked():
            return
        super()._toggle_graph_flip()

    def _block_graph_flip(self) -> None:
        self._flip_blocked_until = max(self._flip_blocked_until, monotonic() + self._FLIP_GUARD_SECONDS)

    def _graph_flip_is_blocked(self) -> bool:
        return self._history_keys.mode is not None or monotonic() < self._flip_blocked_until

    @classmethod
    def _history_key_name(cls, event: QKeyEvent) -> str | None:
        key = event.key()
        if key == Qt.Key.Key_Control:
            return "control"
        if key == Qt.Key.Key_Shift:
            return "shift"
        if key == Qt.Key.Key_Z:
            return "z"

        # Logical key values may follow the active keyboard layout. Support the
        # Russian key on the same physical position as Latin Z as well as the
        # control character produced by Ctrl+Z.
        text = event.text().casefold()
        if text in {"z", "я", "\x1a"}:
            return "z"
        if key in {ord("Я"), ord("я")}:
            return "z"
        if int(event.nativeScanCode()) in cls._PHYSICAL_Z_SCAN_CODES:
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

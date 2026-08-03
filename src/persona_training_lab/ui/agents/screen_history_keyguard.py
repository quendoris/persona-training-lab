from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QPushButton

from persona_training_lab.ui.agents.history_key_state import HISTORY_TOGGLE, HISTORY_UNDO, HistoryKeyState
from persona_training_lab.ui.agents.screen_stateful_fixed import AgentsScreen as _StatefulFixedAgentsScreen


class AgentsScreen(_StatefulFixedAgentsScreen):
    """Own graph history key gestures before Qt can route them elsewhere."""

    _HISTORY_BINDING_IDS = ("history_toggle", "undo_only")
    _HISTORY_SEQUENCES = frozenset({"ctrl+z", "ctrl+shift+z"})
    # Linux evdev codes and their X11/XKB (+8) equivalents.
    _PHYSICAL_SHIFT_SCAN_CODES = frozenset({42, 50, 54, 62})
    _PHYSICAL_Z_SCAN_CODES = frozenset({44, 52})
    _REPEAT_DELAY_MS = 330
    _REPEAT_INTERVAL_MS = 85
    _MODIFIER_POLL_MS = 16
    _FLIP_GUARD_SECONDS = 0.35
    _KEYBOARD_LAYOUT_CHANGE = getattr(QEvent.Type, "KeyboardLayoutChange", None)

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

        # Polling is a positive-only fallback for modifier events consumed by the
        # desktop. Real KeyRelease events remain the authoritative release signal.
        self._modifier_poll = QTimer(self)
        self._modifier_poll.setInterval(self._MODIFIER_POLL_MS)
        self._modifier_poll.timeout.connect(self._poll_physical_modifiers)
        self._modifier_poll.start()

        self._disable_conflicting_history_bindings()
        QTimer.singleShot(0, self._disable_conflicting_history_bindings)

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

        # Internal dialogs deactivate child windows without deactivating the whole
        # application. Only a real application deactivation ends a key gesture.
        if event_type == QEvent.Type.WindowDeactivate:
            return False
        if event_type == QEvent.Type.ApplicationDeactivate:
            self._reset_history_gesture()
            return super().eventFilter(watched, event)

        if self._KEYBOARD_LAYOUT_CHANGE is not None and event_type == self._KEYBOARD_LAYOUT_CHANGE:
            self._handle_keyboard_layout_change()
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
        actions = list(
            self._history_keys.prime_modifiers(
                control=key_name != "control" and control,
                shift=key_name != "shift" and shift,
            )
        )
        actions.extend(self._history_keys.press(key_name))

        # Ctrl and Shift before Z remain available to the desktop layout switch.
        claimed = bool(actions) or self._history_keys.history_gesture_active
        if not claimed:
            return False

        self._block_graph_flip()
        if not event.isAutoRepeat():
            self._dispatch_history_actions(actions)
        return True

    def _handle_history_key_release(self, key_name: str) -> bool:
        if key_name == "shift":
            # XKB may hide Shift from logical modifiers during Ctrl+Shift layout
            # switching, but a physical Shift KeyRelease remains authoritative.
            was_control_down = self._history_keys.control_down
            was_strict = self._history_keys.strict_undo_requested
            claimed = self._history_keys.release("shift")
            self._stop_undo_repeat()
            if claimed or was_control_down or was_strict:
                self._block_graph_flip()
            return claimed or (was_control_down and was_strict)

        claimed = self._history_keys.release(key_name)
        if not claimed:
            return False
        if key_name in {"control", "z"} or not self._history_keys.undo_repeat_active:
            self._stop_undo_repeat()
        self._block_graph_flip()
        return True

    def _handle_keyboard_layout_change(self) -> None:
        control, _shift = self._queried_modifiers()
        if not (control or self._history_keys.control_down):
            return
        self._history_keys.control_down = True
        actions = self._history_keys.latch_layout_shift()
        self._block_graph_flip()
        self._dispatch_history_actions(actions)

    def _poll_physical_modifiers(self) -> None:
        if not self._history_keys_are_active():
            return

        control, shift = self._queried_modifiers()
        actions: list[str] = []

        # Polling can only confirm a pressed modifier. queryKeyboardModifiers()
        # may briefly report False while Ctrl+Shift changes the XKB layout, so it
        # must never release an already observed key.
        if control and not self._history_keys.control_down:
            actions.extend(self._history_keys.press("control"))
        if shift:
            actions.extend(self._history_keys.set_physical_shift(True))

        if actions:
            self._block_graph_flip()
            self._dispatch_history_actions(actions)

    def _dispatch_history_actions(self, actions) -> None:
        seen: set[str] = set()
        for action in actions:
            if action in seen:
                continue
            seen.add(action)
            if action == HISTORY_TOGGLE:
                self._stop_undo_repeat()
                self._toggle_last_history_action()
            elif action == HISTORY_UNDO:
                self._undo_history_only()
                self._arm_undo_repeat()

    def _effective_modifiers(self, event: QKeyEvent) -> tuple[bool, bool]:
        queried_control, queried_shift = self._queried_modifiers()
        modifiers = event.modifiers()
        control = (
            self._history_keys.control_down
            or queried_control
            or bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        )
        shift = (
            self._history_keys.strict_undo_requested
            or queried_shift
            or bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        )
        return control, shift

    @staticmethod
    def _queried_modifiers() -> tuple[bool, bool]:
        modifiers = QGuiApplication.queryKeyboardModifiers()
        return (
            bool(modifiers & Qt.KeyboardModifier.ControlModifier),
            bool(modifiers & Qt.KeyboardModifier.ShiftModifier),
        )

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
        for binding_id in self._HISTORY_BINDING_IDS:
            shortcut = getattr(self, "_shortcuts", {}).get(binding_id)
            if shortcut is not None:
                shortcut.setEnabled(False)
                shortcut.setKey(QKeySequence())
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
        control, shift = self._queried_modifiers()
        modifiers = QGuiApplication.queryKeyboardModifiers()
        guarded = control or shift or bool(
            modifiers & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)
        )
        return (
            self._history_keys.mode is not None
            or self._history_keys.strict_undo_requested
            or guarded
            or monotonic() < self._flip_blocked_until
        )

    @classmethod
    def _history_key_name(cls, event: QKeyEvent) -> str | None:
        key = event.key()
        scan_code = int(event.nativeScanCode())
        if key == Qt.Key.Key_Control:
            return "control"
        if key == Qt.Key.Key_Shift or scan_code in cls._PHYSICAL_SHIFT_SCAN_CODES:
            return "shift"
        if key == Qt.Key.Key_Z:
            return "z"
        text = event.text().casefold()
        if text in {"z", "я", "\x1a"}:
            return "z"
        if key in {ord("Я"), ord("я")}:
            return "z"
        if scan_code in cls._PHYSICAL_Z_SCAN_CODES:
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

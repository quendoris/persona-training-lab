from __future__ import annotations

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QPushButton

from persona_training_lab.ui.agents.history_gesture_lifecycle import HistoryGestureLifecycle
from persona_training_lab.ui.agents.history_key_resolver import HistoryKeyResolver
from persona_training_lab.ui.agents.history_key_state import HISTORY_TOGGLE, HISTORY_UNDO, HistoryKeyState
from persona_training_lab.ui.agents.history_modifier_poller import HistoryModifierPoller
from persona_training_lab.ui.agents.history_repeat_timers import HistoryRepeatTimers
from persona_training_lab.ui.agents.history_shortcut_routing import HistoryShortcutRouting
from persona_training_lab.ui.agents.screen_stateful_fixed import AgentsScreen as _StatefulFixedAgentsScreen
from persona_training_lab.ui.keybindings.manager import KeyBindingManager


_HISTORY_ROUTING = HistoryShortcutRouting()


class AgentsScreen(_StatefulFixedAgentsScreen):
    """Own graph history key gestures before Qt can route them elsewhere."""

    _HISTORY_BINDING_IDS = _HISTORY_ROUTING.binding_ids
    _DEFAULT_GUARDED_SEQUENCES = _HISTORY_ROUTING.default_sequences
    _HISTORY_SEQUENCES = _HISTORY_ROUTING.history_sequences
    _REPEAT_DELAY_MS = 330
    _REPEAT_INTERVAL_MS = 85
    _MODIFIER_POLL_MS = 16
    _FLIP_GUARD_SECONDS = HistoryGestureLifecycle.DEFAULT_FLIP_GUARD_SECONDS
    _KEYBOARD_LAYOUT_CHANGE = getattr(QEvent.Type, "KeyboardLayoutChange", None)

    def __init__(self, view_model, key_binding_manager: KeyBindingManager | None = None) -> None:
        self._key_binding_manager = key_binding_manager or KeyBindingManager()
        self._guarded_history_bindings: set[str] = set()
        super().__init__(view_model)

        self._history_keys = HistoryKeyState()
        self._history_lifecycle = HistoryGestureLifecycle(
            flip_guard_seconds=self._FLIP_GUARD_SECONDS,
        )
        self._history_repeat = HistoryRepeatTimers(
            repeat_allowed=self._repeat_is_allowed,
            on_repeat=self._perform_repeated_undo,
            delay_ms=self._REPEAT_DELAY_MS,
            interval_ms=self._REPEAT_INTERVAL_MS,
            parent=self,
        )

        # Polling is a positive-only fallback for modifier events consumed by the
        # desktop. Real KeyRelease events remain the authoritative release signal.
        self._modifier_poll = HistoryModifierPoller(
            self._poll_physical_modifiers,
            interval_ms=self._MODIFIER_POLL_MS,
            parent=self,
        )

        self._key_binding_manager.bindings_changed.connect(self._apply_key_binding_sequences)
        self._apply_key_binding_sequences()
        QTimer.singleShot(0, self._sync_history_shortcut_routing)

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
        # application. Only a real application deactivation ends a key gesture,
        # while modifier polling follows the actual active-window lifecycle.
        if event_type == QEvent.Type.WindowDeactivate:
            self._modifier_poll.stop()
            return False
        if event_type == QEvent.Type.ApplicationDeactivate:
            self._modifier_poll.stop()
            self._reset_history_gesture()
            return super().eventFilter(watched, event)

        if event_type in (QEvent.Type.ApplicationActivate, QEvent.Type.WindowActivate):
            self._sync_modifier_polling()
        elif watched is self and event_type == QEvent.Type.Hide:
            self._modifier_poll.stop()
        elif watched is self and event_type == QEvent.Type.Show:
            self._sync_modifier_polling()

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
        if key_name == "z" and self._has_extra_history_modifiers(event):
            return False

        control, shift = self._effective_modifiers(event)
        actions = list(
            self._history_keys.prime_modifiers(
                control=key_name != "control" and control,
                shift=key_name != "shift" and shift,
            )
        )
        actions.extend(self._history_keys.press(key_name))
        guarded_actions = self._guarded_actions(actions)

        # Ctrl and Shift before Z remain available to the desktop layout switch.
        claimed = bool(guarded_actions) or self._guarded_history_gesture_active()
        if not claimed:
            return False

        self._block_graph_flip()
        if not event.isAutoRepeat():
            self._dispatch_history_actions(guarded_actions)
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
        if "undo_only" not in self._guarded_history_bindings:
            return
        control, _shift = self._queried_modifiers()
        if not (control or self._history_keys.control_down):
            return
        self._history_keys.control_down = True
        actions = self._guarded_actions(self._history_keys.latch_layout_shift())
        self._block_graph_flip()
        self._dispatch_history_actions(actions)

    def _poll_physical_modifiers(self) -> None:
        if not self._history_keys_are_active() or not self._guarded_history_bindings:
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

        guarded_actions = self._guarded_actions(actions)
        if guarded_actions:
            self._block_graph_flip()
            self._dispatch_history_actions(guarded_actions)

    def _dispatch_history_actions(self, actions) -> None:
        seen: set[str] = set()
        for action in self._guarded_actions(actions):
            if action in seen:
                continue
            seen.add(action)
            if action == HISTORY_TOGGLE:
                self._stop_undo_repeat()
                self._toggle_last_history_action()
            elif action == HISTORY_UNDO:
                self._undo_history_only()
                self._arm_undo_repeat()

    def _guarded_actions(self, actions) -> tuple[str, ...]:
        return _HISTORY_ROUTING.allowed_actions(actions, self._guarded_history_bindings)

    def _guarded_history_gesture_active(self) -> bool:
        return _HISTORY_ROUTING.gesture_is_guarded(
            self._history_keys,
            self._guarded_history_bindings,
        )

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
    def _has_extra_history_modifiers(event: QKeyEvent) -> bool:
        modifiers = event.modifiers()
        extras = Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier
        return bool(modifiers & extras)

    @staticmethod
    def _queried_modifiers() -> tuple[bool, bool]:
        modifiers = QGuiApplication.queryKeyboardModifiers()
        return (
            bool(modifiers & Qt.KeyboardModifier.ControlModifier),
            bool(modifiers & Qt.KeyboardModifier.ShiftModifier),
        )

    def _repeat_is_allowed(self) -> bool:
        return self._history_lifecycle.repeat_is_allowed(
            self._history_keys,
            can_undo=self._state.can_undo(),
            undo_binding_owned="undo_only" in self._guarded_history_bindings,
        )

    def _arm_undo_repeat(self) -> None:
        self._history_repeat.arm()

    def _start_undo_repeat(self) -> None:
        self._history_repeat.start_repeat()

    def _repeat_undo_history(self) -> None:
        self._history_repeat.tick()

    def _perform_repeated_undo(self) -> None:
        self._block_graph_flip()
        self._undo_history_only()

    def _stop_undo_repeat(self) -> None:
        self._history_repeat.stop()

    def _reset_history_gesture(self) -> None:
        self._stop_undo_repeat()
        self._history_keys.reset()
        self._block_graph_flip()

    def _claims_history_override(self, event: QKeyEvent, key_name: str | None) -> bool:
        control, shift = self._effective_modifiers(event)
        return _HISTORY_ROUTING.claims_override(
            key_name=key_name,
            control=control,
            shift=shift,
            has_extra_modifiers=self._has_extra_history_modifiers(event),
            state=self._history_keys,
            guarded_bindings=self._guarded_history_bindings,
        )

    def _apply_key_binding_sequences(self) -> None:
        self._reset_history_gesture_if_ready()
        definitions = {item.binding_id: item for item in self._key_binding_manager.definitions()}
        for binding_id, shortcut in getattr(self, "_shortcuts", {}).items():
            sequence_text = self._key_binding_manager.sequence(binding_id)
            sequence = QKeySequence.fromString(sequence_text, QKeySequence.SequenceFormat.PortableText)
            shortcut.setKey(sequence)
            definition = definitions.get(binding_id)
            if definition is not None:
                shortcut.setAutoRepeat(definition.auto_repeat)
        self._sync_history_shortcut_routing()

    def _reset_history_gesture_if_ready(self) -> None:
        if hasattr(self, "_history_keys") and hasattr(self, "_history_repeat"):
            self._reset_history_gesture()

    def _sync_history_shortcut_routing(self) -> None:
        sequences = {
            binding_id: self._key_binding_manager.sequence(binding_id)
            for binding_id in self._HISTORY_BINDING_IDS
        }
        guarded = set(_HISTORY_ROUTING.guarded_bindings(sequences))
        self._guarded_history_bindings = guarded

        for binding_id in self._HISTORY_BINDING_IDS:
            shortcut = getattr(self, "_shortcuts", {}).get(binding_id)
            if shortcut is not None:
                shortcut.setEnabled(binding_id not in guarded)

        sync_modifier_polling = getattr(self, "_sync_modifier_polling", None)
        if sync_modifier_polling is not None:
            sync_modifier_polling()

    def _sync_modifier_polling(self) -> None:
        if not hasattr(self, "_modifier_poll"):
            return
        self._modifier_poll.set_active(
            bool(self._guarded_history_bindings) and self._history_keys_are_active()
        )

    def _disable_conflicting_history_bindings(self) -> None:
        # Compatibility for older callers and tests.
        self._sync_history_shortcut_routing()

    @staticmethod
    def _normalized_sequence(sequence: str) -> str:
        return _HISTORY_ROUTING.normalized_sequence(sequence)

    @staticmethod
    def _sequence_is_history(sequence: QKeySequence) -> bool:
        return _HISTORY_ROUTING.sequence_is_history(sequence)

    def _toggle_graph_flip(self) -> None:
        if self._graph_flip_is_blocked():
            return
        super()._toggle_graph_flip()

    def _block_graph_flip(self) -> None:
        self._history_lifecycle.block_flip()

    def _graph_flip_is_blocked(self) -> bool:
        control, shift = self._queried_modifiers()
        modifiers = QGuiApplication.queryKeyboardModifiers()
        guarded = control or shift or bool(
            modifiers & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)
        )
        return self._history_lifecycle.flip_is_blocked(
            self._history_keys,
            modifier_guarded=guarded,
        )

    @staticmethod
    def _history_key_name(event: QKeyEvent) -> str | None:
        return HistoryKeyResolver.key_name(event)

    def _history_keys_are_active(self) -> bool:
        app = QApplication.instance()
        if app is None or not self.isVisible() or not self.window().isActiveWindow():
            return False
        if app.activeModalWidget() is not None:
            return False
        focus = app.focusWidget()
        return focus is None or focus.window() is self.window()

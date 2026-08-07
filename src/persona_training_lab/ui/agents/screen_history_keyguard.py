from __future__ import annotations

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QPushButton

from persona_training_lab.ui.agents.history_event_orchestrator import HistoryEventOrchestrator
from persona_training_lab.ui.agents.history_gesture_core import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
    HistoryGestureCore,
    HistoryTransition,
)
from persona_training_lab.ui.agents.history_key_resolver import HistoryKeyResolver
from persona_training_lab.ui.agents.history_modifier_poller import HistoryModifierPoller
from persona_training_lab.ui.agents.history_modifier_snapshot import HistoryModifierSnapshot
from persona_training_lab.ui.agents.history_repeat_timers import HistoryRepeatTimers
from persona_training_lab.ui.agents.history_shortcut_routing import HistoryShortcutRouting
from persona_training_lab.ui.agents.screen_lineage_interactions import (
    AgentsScreen as _LineageInteractionAgentsScreen,
)
from persona_training_lab.ui.keybindings.manager import KeyBindingManager


_HISTORY_ROUTING = HistoryShortcutRouting()


class AgentsScreen(_LineageInteractionAgentsScreen):
    """Own Qt transport for the graph history gesture core."""

    _HISTORY_BINDING_IDS = _HISTORY_ROUTING.binding_ids
    _DEFAULT_GUARDED_SEQUENCES = _HISTORY_ROUTING.default_sequences
    _HISTORY_SEQUENCES = _HISTORY_ROUTING.history_sequences
    _REPEAT_DELAY_MS = 330
    _REPEAT_INTERVAL_MS = 85
    _MODIFIER_POLL_MS = 16
    _FLIP_GUARD_SECONDS = HistoryGestureCore.DEFAULT_FLIP_GUARD_SECONDS
    _KEYBOARD_LAYOUT_CHANGE = getattr(QEvent.Type, "KeyboardLayoutChange", None)

    def __init__(self, view_model, key_binding_manager: KeyBindingManager | None = None) -> None:
        self._key_binding_manager = key_binding_manager or KeyBindingManager()
        self._history_gesture = HistoryGestureCore(
            flip_guard_seconds=self._FLIP_GUARD_SECONDS,
        )
        super().__init__(view_model)

        self._history_repeat = HistoryRepeatTimers(
            delay_ms=self._REPEAT_DELAY_MS,
            interval_ms=self._REPEAT_INTERVAL_MS,
            parent=self,
        )
        self._history_repeat.delay_elapsed.connect(self._start_undo_repeat)
        self._history_repeat.repeat_elapsed.connect(self._repeat_undo_history)

        # Polling is a positive-only fallback for modifier events consumed by the
        # desktop. Real KeyRelease events remain the authoritative release signal.
        self._modifier_poll = HistoryModifierPoller(
            interval_ms=self._MODIFIER_POLL_MS,
            parent=self,
        )
        self._modifier_poll.poll_requested.connect(self._poll_physical_modifiers)
        self._history_events = HistoryEventOrchestrator(
            keyboard_layout_change=self._KEYBOARD_LAYOUT_CHANGE,
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
        decision = self._history_events.route(
            self,
            watched_is_owner=watched is self,
            event=event,
        )
        if decision is not None:
            return decision
        return super().eventFilter(watched, event)

    def _handle_history_key_press(self, event: QKeyEvent, key_name: str) -> bool:
        if not self._history_gesture.has_guarded_bindings:
            return False

        has_extra_modifiers = self._has_extra_history_modifiers(event)
        if key_name == "z" and has_extra_modifiers:
            return False

        control, shift = self._observed_modifiers(event)
        transition = self._history_gesture.press(
            key_name,
            observed_control=control,
            observed_shift=shift,
            has_extra_modifiers=has_extra_modifiers,
            auto_repeat=event.isAutoRepeat(),
        )
        self._apply_history_transition(transition)
        return transition.claimed

    def _handle_history_key_release(self, key_name: str) -> bool:
        transition = self._history_gesture.release(key_name)
        self._apply_history_transition(transition)
        return transition.claimed

    def _handle_keyboard_layout_change(self) -> None:
        if not self._history_gesture.undo_binding_owned:
            return
        control, _shift = self._queried_modifiers()
        transition = self._history_gesture.layout_changed(observed_control=control)
        self._apply_history_transition(transition)

    def _poll_physical_modifiers(self) -> None:
        if not self._history_keys_are_active() or not self._history_gesture.has_guarded_bindings:
            return

        control, shift = self._queried_modifiers()
        transition = self._history_gesture.poll_modifiers(
            observed_control=control,
            observed_shift=shift,
        )
        self._apply_history_transition(transition)

    def _apply_history_transition(self, transition: HistoryTransition) -> None:
        if transition.stop_repeat:
            self._stop_undo_repeat()
        self._dispatch_history_actions(transition.actions)

    def _dispatch_history_actions(self, actions) -> None:
        for action in actions:
            if action == HISTORY_TOGGLE:
                self._stop_undo_repeat()
                self._toggle_last_history_action()
            elif action == HISTORY_UNDO:
                self._undo_history_only()
                self._arm_undo_repeat()

    def _guarded_actions(self, actions) -> tuple[str, ...]:
        return self._history_gesture.allowed_actions(actions)

    def _guarded_history_gesture_active(self) -> bool:
        return self._history_gesture.gesture_is_guarded()

    def _observed_modifiers(self, event: QKeyEvent) -> tuple[bool, bool]:
        """Return only transport observations, never core-derived latch state."""
        queried_control, queried_shift = self._queried_modifiers()
        event_modifiers = HistoryModifierSnapshot.from_qt(event.modifiers())
        return (
            queried_control or event_modifiers.control,
            queried_shift or event_modifiers.shift,
        )

    @staticmethod
    def _has_extra_history_modifiers(event: QKeyEvent) -> bool:
        return HistoryModifierSnapshot.from_qt(event.modifiers()).has_extra_history_modifiers

    @staticmethod
    def _queried_modifiers() -> tuple[bool, bool]:
        modifiers = HistoryModifierSnapshot.current()
        return modifiers.control, modifiers.shift

    @staticmethod
    def _queried_extra_history_modifiers() -> bool:
        return HistoryModifierSnapshot.current().has_extra_history_modifiers

    def _repeat_is_allowed(self) -> bool:
        return self._history_gesture.repeat_is_allowed(can_undo=self._state.can_undo())

    def _arm_undo_repeat(self) -> None:
        if not self._repeat_is_allowed():
            self._history_repeat.stop()
            return
        self._history_repeat.arm()

    def _start_undo_repeat(self) -> None:
        if not self._repeat_is_allowed():
            self._history_repeat.stop()
            return
        self._history_repeat.start_repeat()

    def _repeat_undo_history(self) -> None:
        if not self._repeat_is_allowed():
            self._history_repeat.stop()
            return
        self._perform_repeated_undo()

    def _perform_repeated_undo(self) -> None:
        self._block_graph_flip()
        self._undo_history_only()

    def _stop_undo_repeat(self) -> None:
        self._history_repeat.stop()

    def _reset_history_gesture(self) -> None:
        self._stop_undo_repeat()
        self._history_gesture.reset()

    def _claims_history_override(self, event: QKeyEvent, key_name: str | None) -> bool:
        if not self._history_gesture.has_guarded_bindings:
            return False

        has_extra_modifiers = self._has_extra_history_modifiers(event)
        if key_name == "z" and has_extra_modifiers:
            return False

        control, shift = self._observed_modifiers(event)
        return self._history_gesture.claims_override(
            key_name=key_name,
            observed_control=control,
            observed_shift=shift,
            has_extra_modifiers=has_extra_modifiers,
        )

    def _apply_key_binding_sequences(self) -> None:
        self._reset_history_gesture_if_ready()
        definitions = {item.binding_id: item for item in self._key_binding_manager.definitions()}
        for binding_id, shortcut in getattr(self, "_shortcuts", {}).items():
            sequence_text = self._key_binding_manager.sequence(binding_id)
            sequence = QKeySequence.fromString(
                sequence_text,
                QKeySequence.SequenceFormat.PortableText,
            )
            shortcut.setKey(sequence)
            definition = definitions.get(binding_id)
            if definition is not None:
                shortcut.setAutoRepeat(definition.auto_repeat)
        self._sync_history_shortcut_routing()

    def _reset_history_gesture_if_ready(self) -> None:
        if hasattr(self, "_history_repeat"):
            self._reset_history_gesture()

    def _sync_history_shortcut_routing(self) -> None:
        sequences = {
            binding_id: self._key_binding_manager.sequence(binding_id)
            for binding_id in self._HISTORY_BINDING_IDS
        }
        guarded = _HISTORY_ROUTING.guarded_bindings(sequences)
        self._history_gesture.set_guarded_bindings(guarded)

        for binding_id in self._HISTORY_BINDING_IDS:
            shortcut = getattr(self, "_shortcuts", {}).get(binding_id)
            if shortcut is not None:
                shortcut.setEnabled(binding_id not in guarded)

        self._sync_modifier_polling()

    def _sync_modifier_polling(self) -> None:
        if not hasattr(self, "_modifier_poll"):
            return
        self._modifier_poll.set_active(
            self._history_gesture.has_guarded_bindings and self._history_keys_are_active()
        )

    def _stop_modifier_polling(self) -> None:
        self._modifier_poll.stop()

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
        self._history_gesture.block_flip()

    def _graph_flip_is_blocked(self) -> bool:
        control, shift = self._queried_modifiers()
        has_extra_modifiers = self._queried_extra_history_modifiers()
        guarded = control or shift or has_extra_modifiers
        return self._history_gesture.flip_is_blocked(modifier_guarded=guarded)

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

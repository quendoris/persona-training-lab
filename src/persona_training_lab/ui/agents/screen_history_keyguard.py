from __future__ import annotations

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence

from persona_training_lab.ui.agents.history_binding_ownership import (
    HistoryBindingOwnership,
)
from persona_training_lab.ui.agents.history_event_orchestrator import (
    HistoryEventOrchestrator,
)
from persona_training_lab.ui.agents.history_gesture_core import (
    HistoryGestureCore,
    HistoryTransition as HistoryGestureTransition,
)
from persona_training_lab.ui.agents.history_input_environment import (
    HistoryInputEnvironment,
    HistoryInputEnvironmentSnapshot,
)
from persona_training_lab.ui.agents.history_key_resolver import HistoryKeyResolver
from persona_training_lab.ui.agents.history_modifier_poller import HistoryModifierPoller
from persona_training_lab.ui.agents.history_modifier_snapshot import (
    HistoryModifierSnapshot,
)
from persona_training_lab.ui.agents.history_repeat_timers import HistoryRepeatTimers
from persona_training_lab.ui.agents.history_shortcut_routing import (
    HistoryShortcutRouting,
)
from persona_training_lab.ui.agents.history_transition_orchestrator import (
    HistoryTransitionOrchestrator,
)
from persona_training_lab.ui.agents.screen_lineage_interactions import (
    AgentsScreen as _LineageInteractionAgentsScreen,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.keybindings.shortcut_sync import (
    ShortcutBindingSynchronizer,
)


_HISTORY_ROUTING = HistoryShortcutRouting()


class AgentsScreen(_LineageInteractionAgentsScreen):
    """Own Qt transport for the graph history gesture core."""

    _REPEAT_DELAY_MS = 330
    _REPEAT_INTERVAL_MS = 85
    _MODIFIER_POLL_MS = 16
    _FLIP_GUARD_SECONDS = HistoryGestureCore.DEFAULT_FLIP_GUARD_SECONDS
    _KEYBOARD_LAYOUT_CHANGE = getattr(
        QEvent.Type,
        "KeyboardLayoutChange",
        None,
    )

    def __init__(
        self,
        view_model,
        key_binding_manager: KeyBindingManager | None = None,
        localization: LocalizationManager | None = None,
    ) -> None:
        self._key_binding_manager = (
            key_binding_manager or KeyBindingManager()
        )
        self._history_gesture = HistoryGestureCore(
            flip_guard_seconds=self._FLIP_GUARD_SECONDS,
        )
        super().__init__(view_model, localization)
        self._history_environment = HistoryInputEnvironment()
        self._shortcut_bindings = ShortcutBindingSynchronizer(
            manager=self._key_binding_manager,
            shortcuts=self._shortcuts,
        )
        self._history_binding_ownership = HistoryBindingOwnership(
            routing=_HISTORY_ROUTING,
            gesture=self._history_gesture,
            shortcuts=self._shortcuts,
        )

        self._history_repeat = HistoryRepeatTimers(
            delay_ms=self._REPEAT_DELAY_MS,
            interval_ms=self._REPEAT_INTERVAL_MS,
            parent=self,
        )
        self._history_transition = HistoryTransitionOrchestrator(
            gesture=self._history_gesture,
            repeat=self._history_repeat,
            can_undo=self._state.can_undo,
            block_flip=self._block_graph_flip,
            undo=self._undo_history_only,
            toggle=self._toggle_last_history_action,
        )
        self._history_repeat.delay_elapsed.connect(
            self._history_transition.start_repeat
        )
        self._history_repeat.repeat_elapsed.connect(
            self._history_transition.repeat_tick
        )

        # Polling is a positive-only fallback for modifier events consumed by the
        # desktop. Real KeyRelease events remain the authoritative release signal.
        self._modifier_poll = HistoryModifierPoller(
            interval_ms=self._MODIFIER_POLL_MS,
            parent=self,
        )
        self._modifier_poll.poll_requested.connect(
            self._poll_physical_modifiers
        )
        self._history_events = HistoryEventOrchestrator(
            keyboard_layout_change=self._KEYBOARD_LAYOUT_CHANGE,
        )

        self._key_binding_manager.bindings_changed.connect(
            self._apply_key_binding_sequences
        )
        self._apply_key_binding_sequences()
        QTimer.singleShot(0, self._sync_modifier_polling)

        flip_button = getattr(self, "_flip_button", None)
        if flip_button is not None:
            flip_button.setShortcut(QKeySequence())
            flip_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            flip_button.setAutoDefault(False)
            flip_button.setDefault(False)

        self._history_environment.install_event_filter(self)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        environment = self._history_environment.capture(self)
        decision = self._history_events.route(
            self,
            watched_is_owner=watched is self,
            event=event,
            environment=environment,
        )
        if decision is not None:
            return decision
        return super().eventFilter(watched, event)

    def _handle_history_key_press(
        self,
        event: QKeyEvent,
        key_name: str,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> bool:
        if not self._history_gesture.has_guarded_bindings:
            return False

        has_extra_modifiers = self._has_extra_history_modifiers(event)
        if key_name == "z" and has_extra_modifiers:
            return False

        control, shift = self._observed_modifiers(event, environment)
        transition = self._history_gesture.press(
            key_name,
            observed_control=control,
            observed_shift=shift,
            has_extra_modifiers=has_extra_modifiers,
            auto_repeat=event.isAutoRepeat(),
        )
        self._apply_history_gesture_transition(transition)
        return transition.claimed

    def _handle_history_key_release(self, key_name: str) -> bool:
        transition = self._history_gesture.release(key_name)
        self._apply_history_gesture_transition(transition)
        return transition.claimed

    def _handle_keyboard_layout_change(
        self,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> None:
        if not self._history_gesture.undo_binding_owned:
            return
        transition = self._history_gesture.layout_changed(
            observed_control=environment.modifiers.control
        )
        self._apply_history_gesture_transition(transition)

    def _poll_physical_modifiers(self) -> None:
        environment = self._history_environment.capture(self)
        if (
            not environment.input_active
            or not self._history_gesture.has_guarded_bindings
        ):
            return

        transition = self._history_gesture.poll_modifiers(
            observed_control=environment.modifiers.control,
            observed_shift=environment.modifiers.shift,
        )
        self._apply_history_gesture_transition(transition)

    def _apply_history_gesture_transition(
        self,
        transition: HistoryGestureTransition,
    ) -> None:
        self._history_transition.apply(transition)

    def _guarded_actions(self, actions) -> tuple[str, ...]:
        return self._history_gesture.allowed_actions(actions)

    def _guarded_history_gesture_active(self) -> bool:
        return self._history_gesture.gesture_is_guarded()

    @staticmethod
    def _observed_modifiers(
        event: QKeyEvent,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> tuple[bool, bool]:
        """Merge one captured environment with event-local modifier facts."""

        event_modifiers = HistoryModifierSnapshot.from_qt(
            event.modifiers()
        )
        return (
            environment.modifiers.control or event_modifiers.control,
            environment.modifiers.shift or event_modifiers.shift,
        )

    @staticmethod
    def _has_extra_history_modifiers(event: QKeyEvent) -> bool:
        return HistoryModifierSnapshot.from_qt(
            event.modifiers()
        ).has_extra_history_modifiers

    def _reset_history_gesture(self) -> None:
        self._history_transition.reset()

    def _claims_history_override(
        self,
        event: QKeyEvent,
        key_name: str | None,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> bool:
        if not self._history_gesture.has_guarded_bindings:
            return False

        has_extra_modifiers = self._has_extra_history_modifiers(event)
        if key_name == "z" and has_extra_modifiers:
            return False

        control, shift = self._observed_modifiers(event, environment)
        return self._history_gesture.claims_override(
            key_name=key_name,
            observed_control=control,
            observed_shift=shift,
            has_extra_modifiers=has_extra_modifiers,
        )

    def _apply_key_binding_sequences(self) -> None:
        self._reset_history_gesture()
        sequences = self._shortcut_bindings.sync()
        self._history_binding_ownership.sync(sequences)
        self._sync_modifier_polling()

    def _sync_modifier_polling(
        self,
        environment: HistoryInputEnvironmentSnapshot | None = None,
    ) -> None:
        if not hasattr(self, "_modifier_poll"):
            return
        snapshot = environment or self._history_environment.capture(self)
        self._modifier_poll.set_active(
            self._history_gesture.has_guarded_bindings
            and snapshot.input_active
        )

    def _stop_modifier_polling(self) -> None:
        self._modifier_poll.stop()

    def _toggle_graph_flip(self) -> None:
        if self._graph_flip_is_blocked():
            return
        super()._toggle_graph_flip()

    def _block_graph_flip(self) -> None:
        self._history_gesture.block_flip()

    def _graph_flip_is_blocked(self) -> bool:
        modifiers = self._history_environment.capture(self).modifiers
        modifier_guarded = (
            modifiers.control
            or modifiers.shift
            or modifiers.has_extra_history_modifiers
        )
        return self._history_gesture.flip_is_blocked(
            modifier_guarded=modifier_guarded
        )

    @staticmethod
    def _history_key_name(event: QKeyEvent) -> str | None:
        return HistoryKeyResolver.key_name(event)

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import ClassVar


HISTORY_TOGGLE = "toggle"
HISTORY_UNDO = "undo"

HISTORY_TOGGLE_BINDING = "history_toggle"
HISTORY_UNDO_BINDING = "undo_only"
HISTORY_BINDING_IDS = frozenset({HISTORY_TOGGLE_BINDING, HISTORY_UNDO_BINDING})


class _HistoryMode(Enum):
    TOGGLE = "toggle"
    UNDO_ONLY = "undo_only"
    SPENT = "spent"


@dataclass(frozen=True, slots=True)
class HistoryTransition:
    """Effects emitted by one history-gesture state transition."""

    claimed: bool = False
    actions: tuple[str, ...] = ()
    stop_repeat: bool = False


@dataclass(slots=True)
class HistoryGestureCore:
    """Pure state machine for guarded history gestures.

    The core owns gesture state, guarded-binding policy, repeat eligibility, and
    the graph-flip guard. Qt transports only normalize events and execute emitted
    actions.
    """

    DEFAULT_FLIP_GUARD_SECONDS: ClassVar[float] = 0.35

    flip_guard_seconds: float = DEFAULT_FLIP_GUARD_SECONDS
    clock: Callable[[], float] = field(
        default=monotonic,
        repr=False,
        compare=False,
    )
    _guarded_bindings: frozenset[str] = field(default_factory=frozenset, init=False)
    control_down: bool = field(default=False, init=False)
    shift_down: bool = field(default=False, init=False)
    layout_shift_latched: bool = field(default=False, init=False)
    z_down: bool = field(default=False, init=False)
    _mode: _HistoryMode | None = field(default=None, init=False, repr=False)
    _flip_blocked_until: float = field(default=0.0, init=False, repr=False)

    @property
    def guarded_bindings(self) -> frozenset[str]:
        return self._guarded_bindings

    @property
    def has_guarded_bindings(self) -> bool:
        return bool(self._guarded_bindings)

    @property
    def undo_binding_owned(self) -> bool:
        return HISTORY_UNDO_BINDING in self._guarded_bindings

    @property
    def mode(self) -> str | None:
        return self._mode.value if self._mode is not None else None

    @property
    def flip_blocked_until(self) -> float:
        return self._flip_blocked_until

    @property
    def shift_latched(self) -> bool:
        """Compatibility view derived from the two authoritative Shift sources."""
        return self.shift_down or self.layout_shift_latched

    @property
    def strict_undo_requested(self) -> bool:
        return self.shift_down or self.layout_shift_latched

    @property
    def history_gesture_active(self) -> bool:
        return self.control_down and self.z_down

    @property
    def undo_repeat_active(self) -> bool:
        return (
            self.history_gesture_active
            and self.strict_undo_requested
            and self._mode is _HistoryMode.UNDO_ONLY
        )

    def set_guarded_bindings(self, binding_ids: Iterable[str]) -> frozenset[str]:
        self._guarded_bindings = frozenset(
            binding_id for binding_id in binding_ids if binding_id in HISTORY_BINDING_IDS
        )
        if not self._guarded_bindings:
            self._clear_gesture_state()
        return self._guarded_bindings

    def allowed_actions(self, actions: Iterable[str]) -> tuple[str, ...]:
        allowed: list[str] = []
        for action in actions:
            if action == HISTORY_TOGGLE and HISTORY_TOGGLE_BINDING in self._guarded_bindings:
                allowed.append(action)
            elif action == HISTORY_UNDO and HISTORY_UNDO_BINDING in self._guarded_bindings:
                allowed.append(action)
        return tuple(allowed)

    def gesture_is_guarded(self) -> bool:
        if not self.history_gesture_active:
            return False
        if self.strict_undo_requested:
            return HISTORY_UNDO_BINDING in self._guarded_bindings
        return HISTORY_TOGGLE_BINDING in self._guarded_bindings

    def effective_modifiers(
        self,
        *,
        observed_control: bool,
        observed_shift: bool,
    ) -> tuple[bool, bool]:
        """Combine external observations with state without mutating either source."""
        return (
            self.control_down or observed_control,
            self.strict_undo_requested or observed_shift,
        )

    def press(
        self,
        key_name: str,
        *,
        observed_control: bool,
        observed_shift: bool,
        has_extra_modifiers: bool,
        auto_repeat: bool,
    ) -> HistoryTransition:
        if not self.has_guarded_bindings:
            return HistoryTransition()
        if key_name == "z" and has_extra_modifiers:
            return HistoryTransition()

        # Only externally observed modifiers may prime physical state. Internal
        # latches (notably KeyboardLayoutChange) affect chord semantics but must
        # never be fed back as fresh physical Shift observations.
        actions = list(
            self._prime_modifiers(
                control=key_name != "control" and observed_control,
                shift=key_name != "shift" and observed_shift,
            )
        )
        actions.extend(self._press_key(key_name))
        guarded_actions = self.allowed_actions(actions)

        claimed = bool(guarded_actions) or self.gesture_is_guarded()
        if not claimed:
            return HistoryTransition()

        self.block_flip()
        return HistoryTransition(
            claimed=True,
            actions=() if auto_repeat else guarded_actions,
        )

    def release(self, key_name: str) -> HistoryTransition:
        if not self.has_guarded_bindings:
            return HistoryTransition()

        if key_name == "shift":
            was_control_down = self.control_down
            was_strict = self.strict_undo_requested
            claimed = self._release_key("shift")
            if claimed or was_control_down or was_strict:
                self.block_flip()
            return HistoryTransition(
                claimed=claimed or (was_control_down and was_strict),
                stop_repeat=True,
            )

        claimed = self._release_key(key_name)
        if not claimed:
            return HistoryTransition()

        stop_repeat = key_name in {"control", "z"} or not self.undo_repeat_active
        self.block_flip()
        return HistoryTransition(claimed=True, stop_repeat=stop_repeat)

    def layout_changed(self, *, observed_control: bool) -> HistoryTransition:
        if not self.undo_binding_owned:
            return HistoryTransition()
        if not (observed_control or self.control_down):
            return HistoryTransition()

        self.control_down = True
        actions = self.allowed_actions(self._latch_layout_shift())
        self.block_flip()
        return HistoryTransition(actions=actions)

    def poll_modifiers(
        self,
        *,
        observed_control: bool,
        observed_shift: bool,
    ) -> HistoryTransition:
        if not self.has_guarded_bindings:
            return HistoryTransition()

        actions: list[str] = []
        if observed_control and not self.control_down:
            actions.extend(self._press_key("control"))
        if observed_shift:
            actions.extend(self._set_physical_shift(True))

        guarded_actions = self.allowed_actions(actions)
        if guarded_actions:
            self.block_flip()
        return HistoryTransition(actions=guarded_actions)

    def claims_override(
        self,
        *,
        key_name: str | None,
        observed_control: bool,
        observed_shift: bool,
        has_extra_modifiers: bool,
    ) -> bool:
        if key_name is None or not self._guarded_bindings:
            return False
        if key_name == "z" and has_extra_modifiers:
            return False

        control, shift = self.effective_modifiers(
            observed_control=observed_control,
            observed_shift=observed_shift,
        )
        if key_name == "z" and control:
            binding_id = HISTORY_UNDO_BINDING if shift else HISTORY_TOGGLE_BINDING
            return binding_id in self._guarded_bindings
        if key_name == "shift" and self.control_down and self.z_down:
            return HISTORY_UNDO_BINDING in self._guarded_bindings
        if key_name == "control" and self.z_down:
            return self.gesture_is_guarded()
        return self._mode is not None and key_name in {"control", "shift", "z"}

    def repeat_is_allowed(self, *, can_undo: bool) -> bool:
        return self.undo_binding_owned and self.undo_repeat_active and can_undo

    def block_flip(self) -> float:
        deadline = self.clock() + self.flip_guard_seconds
        self._flip_blocked_until = max(self._flip_blocked_until, deadline)
        return self._flip_blocked_until

    def flip_is_blocked(self, *, modifier_guarded: bool) -> bool:
        return (
            self._mode is not None
            or self.strict_undo_requested
            or modifier_guarded
            or self.clock() < self._flip_blocked_until
        )

    def reset(self) -> None:
        self._clear_gesture_state()
        self.block_flip()

    def _clear_gesture_state(self) -> None:
        self.control_down = False
        self.shift_down = False
        self.layout_shift_latched = False
        self.z_down = False
        self._mode = None

    def _prime_modifiers(self, *, control: bool, shift: bool) -> tuple[str, ...]:
        self.control_down = self.control_down or control
        if shift:
            return self._set_physical_shift(True)
        return ()

    def _set_physical_shift(self, down: bool) -> tuple[str, ...]:
        if down:
            already_down = self.shift_down
            self.shift_down = True
            if already_down:
                return ()
            return self._activate_chord()

        self.shift_down = False
        self.layout_shift_latched = False
        if self._mode is _HistoryMode.UNDO_ONLY and self.z_down:
            self._mode = _HistoryMode.SPENT
        return ()

    def _latch_layout_shift(self) -> tuple[str, ...]:
        if not self.control_down:
            return ()
        self.layout_shift_latched = True
        return self._activate_chord()

    def _press_key(self, key_name: str) -> tuple[str, ...]:
        if key_name == "control":
            if self.control_down:
                return ()
            self.control_down = True
        elif key_name == "shift":
            return self._set_physical_shift(True)
        elif key_name == "z":
            if self.z_down:
                return ()
            self.z_down = True
        else:
            return ()
        return self._activate_chord()

    def _release_key(self, key_name: str) -> bool:
        was_history_gesture = self.history_gesture_active or self._mode is not None
        if key_name == "control":
            self.control_down = False
            self.layout_shift_latched = False
            self._mode = None
        elif key_name == "shift":
            self._set_physical_shift(False)
        elif key_name == "z":
            self.z_down = False
            self._mode = None
        return was_history_gesture

    def _activate_chord(self) -> tuple[str, ...]:
        if not (self.control_down and self.z_down):
            return ()
        if self.strict_undo_requested:
            if self._mode is not _HistoryMode.UNDO_ONLY:
                self._mode = _HistoryMode.UNDO_ONLY
                return (HISTORY_UNDO,)
            return ()
        if self._mode is None:
            self._mode = _HistoryMode.TOGGLE
            return (HISTORY_TOGGLE,)
        return ()

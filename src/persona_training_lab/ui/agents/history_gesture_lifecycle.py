from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic
from typing import ClassVar

from persona_training_lab.ui.agents.history_key_state import HistoryKeyState


@dataclass(slots=True)
class HistoryGestureLifecycle:
    """Own history-repeat eligibility and the graph-flip guard deadline."""

    DEFAULT_FLIP_GUARD_SECONDS: ClassVar[float] = 0.35

    flip_guard_seconds: float = DEFAULT_FLIP_GUARD_SECONDS
    clock: Callable[[], float] = field(
        default=monotonic,
        repr=False,
        compare=False,
    )
    _flip_blocked_until: float = field(default=0.0, init=False, repr=False)

    @property
    def flip_blocked_until(self) -> float:
        return self._flip_blocked_until

    def block_flip(self) -> float:
        deadline = self.clock() + self.flip_guard_seconds
        self._flip_blocked_until = max(self._flip_blocked_until, deadline)
        return self._flip_blocked_until

    def flip_is_blocked(
        self,
        state: HistoryKeyState,
        *,
        modifier_guarded: bool,
    ) -> bool:
        return (
            state.mode is not None
            or state.strict_undo_requested
            or modifier_guarded
            or self.clock() < self._flip_blocked_until
        )

    @staticmethod
    def repeat_is_allowed(
        state: HistoryKeyState,
        *,
        can_undo: bool,
        undo_binding_owned: bool,
    ) -> bool:
        return (
            undo_binding_owned
            and state.undo_repeat_active
            and can_undo
        )

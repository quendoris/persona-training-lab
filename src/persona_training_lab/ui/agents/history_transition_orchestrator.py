from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

from persona_training_lab.ui.agents.history_gesture_core import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
    HistoryGestureCore,
    HistoryTransition,
)


class HistoryRepeatTransport(Protocol):
    def arm(self) -> None: ...

    def start_repeat(self) -> None: ...

    def stop(self) -> None: ...


@dataclass(slots=True)
class HistoryTransitionOrchestrator:
    """Execute history transitions without owning Qt event routing or timers."""

    gesture: HistoryGestureCore
    repeat: HistoryRepeatTransport
    can_undo: Callable[[], bool]
    block_flip: Callable[[], None]
    undo: Callable[[], None]
    toggle: Callable[[], None]

    def apply(self, transition: HistoryTransition) -> None:
        if transition.stop_repeat:
            self.stop_repeat()
        self.dispatch(transition.actions)

    def dispatch(self, actions: Iterable[str]) -> None:
        for action in actions:
            if action == HISTORY_TOGGLE:
                self.stop_repeat()
                self.toggle()
            elif action == HISTORY_UNDO:
                self.undo()
                self.arm_repeat()

    def repeat_is_allowed(self) -> bool:
        return self.gesture.repeat_is_allowed(can_undo=self.can_undo())

    def arm_repeat(self) -> None:
        if not self.repeat_is_allowed():
            self.repeat.stop()
            return
        self.repeat.arm()

    def start_repeat(self) -> None:
        if not self.repeat_is_allowed():
            self.repeat.stop()
            return
        self.repeat.start_repeat()

    def repeat_tick(self) -> None:
        if not self.repeat_is_allowed():
            self.repeat.stop()
            return
        self.block_flip()
        self.undo()

    def stop_repeat(self) -> None:
        self.repeat.stop()

    def reset(self) -> None:
        self.stop_repeat()
        self.gesture.reset()

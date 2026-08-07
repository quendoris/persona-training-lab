from __future__ import annotations

from persona_training_lab.ui.agents.history_gesture_lifecycle import (
    HistoryGestureLifecycle,
)
from persona_training_lab.ui.agents.history_key_state import HistoryKeyState


class _Clock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_flip_guard_deadline_extends_but_never_moves_backwards() -> None:
    clock = _Clock(10.0)
    lifecycle = HistoryGestureLifecycle(
        flip_guard_seconds=0.35,
        clock=clock,
    )

    assert lifecycle.block_flip() == 10.35

    clock.value = 10.1
    assert lifecycle.block_flip() == 10.45

    clock.value = 10.05
    assert lifecycle.block_flip() == 10.45


def test_flip_guard_expires_only_after_deadline() -> None:
    clock = _Clock(2.0)
    lifecycle = HistoryGestureLifecycle(clock=clock)
    lifecycle.block_flip()
    state = HistoryKeyState()

    clock.value = 2.349
    assert lifecycle.flip_is_blocked(state, modifier_guarded=False) is True

    clock.value = 2.35
    assert lifecycle.flip_is_blocked(state, modifier_guarded=False) is False


def test_active_history_state_blocks_flip_without_time_guard() -> None:
    clock = _Clock(50.0)
    lifecycle = HistoryGestureLifecycle(clock=clock)
    state = HistoryKeyState()
    state.press("control")
    state.press("z")

    assert lifecycle.flip_is_blocked(state, modifier_guarded=False) is True


def test_external_modifier_guard_blocks_flip_without_history_state() -> None:
    lifecycle = HistoryGestureLifecycle(clock=_Clock(100.0))

    assert lifecycle.flip_is_blocked(
        HistoryKeyState(),
        modifier_guarded=True,
    ) is True


def test_repeat_requires_owned_strict_gesture_and_available_undo() -> None:
    state = HistoryKeyState()
    state.press("control")
    state.press("shift")
    state.press("z")

    assert HistoryGestureLifecycle.repeat_is_allowed(
        state,
        can_undo=True,
        undo_binding_owned=True,
    ) is True
    assert HistoryGestureLifecycle.repeat_is_allowed(
        state,
        can_undo=False,
        undo_binding_owned=True,
    ) is False
    assert HistoryGestureLifecycle.repeat_is_allowed(
        state,
        can_undo=True,
        undo_binding_owned=False,
    ) is False


def test_repeat_stops_when_strict_gesture_ends() -> None:
    state = HistoryKeyState()
    state.press("control")
    state.press("shift")
    state.press("z")
    state.release("z")

    assert HistoryGestureLifecycle.repeat_is_allowed(
        state,
        can_undo=True,
        undo_binding_owned=True,
    ) is False

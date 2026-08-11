from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.ui.agents.history_gesture_core import HistoryTransition
from persona_training_lab.ui.agents.history_transition_orchestrator import (
    HistoryTransitionOrchestrator,
)
from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


class _RepeatTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def arm(self) -> None:
        self.calls.append("arm")

    def start_repeat(self) -> None:
        self.calls.append("start")

    def stop(self) -> None:
        self.calls.append("stop")


class _GestureProbe:
    def __init__(self, allowed: list[bool], calls: list[str] | None = None) -> None:
        self._allowed = allowed
        self._calls = calls

    def repeat_is_allowed(self, *, can_undo: bool) -> bool:
        return self._allowed[0] and can_undo

    def reset(self) -> None:
        if self._calls is not None:
            self._calls.append("reset")


def _orchestrator(
    transport: _RepeatTransport,
    allowed: list[bool],
    calls: list[str] | None = None,
) -> HistoryTransitionOrchestrator:
    effects = calls if calls is not None else []
    return HistoryTransitionOrchestrator(
        gesture=_GestureProbe(allowed, effects),  # type: ignore[arg-type]
        repeat=transport,
        can_undo=lambda: True,
        block_flip=lambda: effects.append("block"),
        undo=lambda: effects.append("undo"),
        toggle=lambda: effects.append("toggle"),
    )


def test_arm_repeat_checks_live_permission_before_transport() -> None:
    transport = _RepeatTransport()
    allowed = [True]
    orchestrator = _orchestrator(transport, allowed)

    orchestrator.arm_repeat()
    allowed[0] = False
    orchestrator.arm_repeat()

    assert transport.calls == ["arm", "stop"]


def test_delay_expiry_rechecks_permission_before_repeat_phase() -> None:
    transport = _RepeatTransport()
    allowed = [True]
    orchestrator = _orchestrator(transport, allowed)

    orchestrator.start_repeat()
    allowed[0] = False
    orchestrator.start_repeat()

    assert transport.calls == ["start", "stop"]


def test_repeat_tick_rechecks_permission_before_undo_effect() -> None:
    transport = _RepeatTransport()
    allowed = [True]
    calls: list[str] = []
    orchestrator = _orchestrator(transport, allowed, calls)

    orchestrator.repeat_tick()
    allowed[0] = False
    orchestrator.repeat_tick()

    assert calls == ["block", "undo"]
    assert transport.calls == ["stop"]


def test_repeated_undo_effect_blocks_flip_before_mutating_history() -> None:
    transport = _RepeatTransport()
    calls: list[str] = []
    orchestrator = _orchestrator(transport, [True], calls)

    orchestrator.repeat_tick()

    assert calls == ["block", "undo"]


def test_binding_reset_waits_until_repeat_transport_exists() -> None:
    calls: list[str] = []
    screen = SimpleNamespace(
        _reset_history_gesture=lambda: calls.append("reset"),
    )

    AgentsScreen._reset_history_gesture_if_ready(screen)  # type: ignore[arg-type]
    assert calls == []

    screen._history_repeat = object()
    AgentsScreen._reset_history_gesture_if_ready(screen)  # type: ignore[arg-type]

    assert calls == ["reset"]


def test_transition_stops_repeat_before_dispatching_actions() -> None:
    transport = _RepeatTransport()
    calls: list[str] = []
    orchestrator = _orchestrator(transport, [True], calls)
    transition = HistoryTransition(
        actions=("undo",),
        stop_repeat=True,
    )

    orchestrator.apply(transition)

    assert transport.calls == ["stop", "arm"]
    assert calls == ["undo"]


def test_gesture_reset_stops_repeat_before_resetting_core() -> None:
    transport = _RepeatTransport()
    calls: list[str] = []
    orchestrator = _orchestrator(transport, [True], calls)

    orchestrator.reset()

    assert transport.calls == ["stop"]
    assert calls == ["reset"]

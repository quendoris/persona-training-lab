from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.ui.agents.history_gesture_core import HistoryTransition
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


def test_arm_repeat_checks_live_permission_before_transport() -> None:
    transport = _RepeatTransport()
    allowed = [True]
    screen = SimpleNamespace(
        _history_repeat=transport,
        _repeat_is_allowed=lambda: allowed[0],
    )

    AgentsScreen._arm_undo_repeat(screen)  # type: ignore[arg-type]
    allowed[0] = False
    AgentsScreen._arm_undo_repeat(screen)  # type: ignore[arg-type]

    assert transport.calls == ["arm", "stop"]


def test_delay_expiry_rechecks_permission_before_repeat_phase() -> None:
    transport = _RepeatTransport()
    allowed = [True]
    screen = SimpleNamespace(
        _history_repeat=transport,
        _repeat_is_allowed=lambda: allowed[0],
    )

    AgentsScreen._start_undo_repeat(screen)  # type: ignore[arg-type]
    allowed[0] = False
    AgentsScreen._start_undo_repeat(screen)  # type: ignore[arg-type]

    assert transport.calls == ["start", "stop"]


def test_repeat_tick_rechecks_permission_before_undo_effect() -> None:
    transport = _RepeatTransport()
    allowed = [True]
    calls: list[str] = []
    screen = SimpleNamespace(
        _history_repeat=transport,
        _repeat_is_allowed=lambda: allowed[0],
        _perform_repeated_undo=lambda: calls.append("undo"),
    )

    AgentsScreen._repeat_undo_history(screen)  # type: ignore[arg-type]
    allowed[0] = False
    AgentsScreen._repeat_undo_history(screen)  # type: ignore[arg-type]

    assert calls == ["undo"]
    assert transport.calls == ["stop"]


def test_repeated_undo_effect_blocks_flip_before_mutating_history() -> None:
    calls: list[str] = []
    screen = SimpleNamespace(
        _block_graph_flip=lambda: calls.append("block"),
        _undo_history_only=lambda: calls.append("undo"),
    )

    AgentsScreen._perform_repeated_undo(screen)  # type: ignore[arg-type]

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
    calls: list[object] = []
    screen = SimpleNamespace(
        _stop_undo_repeat=lambda: calls.append("stop"),
        _dispatch_history_actions=lambda actions: calls.append(("dispatch", actions)),
    )
    transition = HistoryTransition(
        actions=("undo",),
        stop_repeat=True,
    )

    AgentsScreen._apply_history_transition(screen, transition)  # type: ignore[arg-type]

    assert calls == ["stop", ("dispatch", ("undo",))]


def test_gesture_reset_stops_repeat_before_resetting_core() -> None:
    calls: list[str] = []
    gesture = SimpleNamespace(reset=lambda: calls.append("reset"))
    screen = SimpleNamespace(
        _history_gesture=gesture,
        _stop_undo_repeat=lambda: calls.append("stop"),
    )

    AgentsScreen._reset_history_gesture(screen)  # type: ignore[arg-type]

    assert calls == ["stop", "reset"]

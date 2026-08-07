from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


class _RepeatTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def arm(self) -> None:
        self.calls.append("arm")

    def start_repeat(self) -> None:
        self.calls.append("start")

    def tick(self) -> None:
        self.calls.append("tick")

    def stop(self) -> None:
        self.calls.append("stop")


def test_history_repeat_hooks_delegate_to_composed_transport() -> None:
    transport = _RepeatTransport()
    screen = SimpleNamespace(_history_repeat=transport)

    AgentsScreen._arm_undo_repeat(screen)  # type: ignore[arg-type]
    AgentsScreen._start_undo_repeat(screen)  # type: ignore[arg-type]
    AgentsScreen._repeat_undo_history(screen)  # type: ignore[arg-type]
    AgentsScreen._stop_undo_repeat(screen)  # type: ignore[arg-type]

    assert transport.calls == ["arm", "start", "tick", "stop"]


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

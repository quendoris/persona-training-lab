from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QEvent

from persona_training_lab.ui.agents.history_gesture_core import (
    HISTORY_TOGGLE,
    HISTORY_UNDO,
)
from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


class _EventRouterProbe:
    def __init__(self) -> None:
        self.calls: list[tuple[object, bool, QEvent]] = []

    def route(self, port, *, watched_is_owner: bool, event: QEvent) -> bool:
        self.calls.append((port, watched_is_owner, event))
        return True


class _ModifierPollProbe:
    def __init__(self) -> None:
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class _NoPolicyProbe:
    def allowed_actions(self, _actions):
        raise AssertionError("adapter must not re-evaluate core action policy")


def test_event_filter_delegates_owner_identity_and_returns_orchestrator_decision() -> None:
    router = _EventRouterProbe()
    screen = SimpleNamespace(_history_events=router)
    event = QEvent(QEvent.Type.User)

    result = AgentsScreen.eventFilter(screen, screen, event)  # type: ignore[arg-type]

    assert result is True
    assert router.calls == [(screen, True, event)]


def test_stop_modifier_polling_remains_a_thin_transport_adapter() -> None:
    poller = _ModifierPollProbe()
    screen = SimpleNamespace(_modifier_poll=poller)

    AgentsScreen._stop_modifier_polling(screen)  # type: ignore[arg-type]

    assert poller.stop_calls == 1


def test_dispatch_executes_transition_actions_without_rechecking_policy() -> None:
    calls: list[str] = []
    screen = SimpleNamespace(
        _history_gesture=_NoPolicyProbe(),
        _stop_undo_repeat=lambda: calls.append("stop"),
        _toggle_last_history_action=lambda: calls.append("toggle"),
        _undo_history_only=lambda: calls.append("undo"),
        _arm_undo_repeat=lambda: calls.append("arm"),
    )

    AgentsScreen._dispatch_history_actions(
        screen,
        (HISTORY_TOGGLE, HISTORY_UNDO, HISTORY_TOGGLE),
    )  # type: ignore[arg-type]

    assert calls == ["stop", "toggle", "undo", "arm", "stop", "toggle"]

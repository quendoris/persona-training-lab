from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QEvent

from persona_training_lab.ui.agents.history_gesture_core import HistoryTransition
from persona_training_lab.ui.agents.history_input_environment import (
    HistoryInputEnvironmentSnapshot,
)
from persona_training_lab.ui.agents.history_modifier_snapshot import (
    HistoryModifierSnapshot,
)
from persona_training_lab.ui.agents.screen_history_transport import AgentsScreen
from persona_training_lab.ui.agents.screen_lineage_interactions import (
    AgentsScreen as _LineageInteractionAgentsScreen,
)


class _EventRouterProbe:
    def __init__(self) -> None:
        self.calls: list[
            tuple[object, bool, QEvent, HistoryInputEnvironmentSnapshot]
        ] = []

    def route(
        self,
        port,
        *,
        watched_is_owner: bool,
        event: QEvent,
        environment: HistoryInputEnvironmentSnapshot,
    ) -> bool:
        self.calls.append((port, watched_is_owner, event, environment))
        return True


class _EnvironmentProbe:
    def __init__(self, snapshot: HistoryInputEnvironmentSnapshot) -> None:
        self.snapshot = snapshot
        self.capture_calls = 0

    def capture(self, _owner) -> HistoryInputEnvironmentSnapshot:
        self.capture_calls += 1
        return self.snapshot


class _ModifierPollProbe:
    def __init__(self) -> None:
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class _TransitionProbe:
    def __init__(self) -> None:
        self.calls: list[HistoryTransition] = []

    def apply(self, transition: HistoryTransition) -> None:
        self.calls.append(transition)


def test_event_filter_captures_one_environment_and_delegates_owner_identity() -> None:
    snapshot = HistoryInputEnvironmentSnapshot(
        modifiers=HistoryModifierSnapshot(control=True),
        input_active=True,
    )
    environment = _EnvironmentProbe(snapshot)
    router = _EventRouterProbe()
    screen = SimpleNamespace(
        _history_environment=environment,
        _history_events=router,
    )
    event = QEvent(QEvent.Type.User)

    result = AgentsScreen.eventFilter(screen, screen, event)  # type: ignore[arg-type]

    assert result is True
    assert environment.capture_calls == 1
    assert router.calls == [(screen, True, event, snapshot)]


def test_stop_modifier_polling_remains_a_thin_transport_adapter() -> None:
    poller = _ModifierPollProbe()
    screen = SimpleNamespace(_modifier_poll=poller)

    AgentsScreen._stop_modifier_polling(screen)  # type: ignore[arg-type]

    assert poller.stop_calls == 1


def test_gesture_transition_application_remains_a_thin_screen_adapter() -> None:
    assert (
        AgentsScreen._apply_history_transition
        is _LineageInteractionAgentsScreen._apply_history_transition
    )

    orchestrator = _TransitionProbe()
    screen = SimpleNamespace(_history_transition=orchestrator)
    transition = HistoryTransition(actions=("toggle",))

    AgentsScreen._apply_history_gesture_transition(
        screen,
        transition,
    )  # type: ignore[arg-type]

    assert orchestrator.calls == [transition]

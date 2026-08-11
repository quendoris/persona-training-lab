from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.history_input_environment import (
    HistoryInputEnvironment,
    HistoryInputEnvironmentSnapshot,
)
from persona_training_lab.ui.agents.history_modifier_snapshot import (
    HistoryModifierSnapshot,
)
from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


class _GestureProbe:
    def __init__(self) -> None:
        self.modifier_guarded: list[bool] = []

    def flip_is_blocked(self, *, modifier_guarded: bool) -> bool:
        self.modifier_guarded.append(modifier_guarded)
        return modifier_guarded


class _EnvironmentProbe:
    def __init__(self, snapshot: HistoryInputEnvironmentSnapshot) -> None:
        self.snapshot = snapshot
        self.capture_calls = 0

    def capture(self, _owner) -> HistoryInputEnvironmentSnapshot:
        self.capture_calls += 1
        return self.snapshot


def _environment_snapshot(
    *,
    control: bool = False,
    shift: bool = False,
    alt: bool = False,
    meta: bool = False,
    input_active: bool = True,
) -> HistoryInputEnvironmentSnapshot:
    return HistoryInputEnvironmentSnapshot(
        modifiers=HistoryModifierSnapshot(
            control=control,
            shift=shift,
            alt=alt,
            meta=meta,
        ),
        input_active=input_active,
    )


def test_observed_modifiers_are_transport_facts_without_core_feedback() -> None:
    environment = _EnvironmentProbe(_environment_snapshot(shift=True))
    screen = SimpleNamespace(_history_environment=environment)
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Z,
        Qt.KeyboardModifier.ControlModifier,
        "z",
    )

    observed = AgentsScreen._observed_modifiers(screen, event)  # type: ignore[arg-type]

    assert observed == (True, True)
    assert environment.capture_calls == 1


def test_graph_flip_guard_uses_one_coherent_environment_snapshot() -> None:
    environment = _EnvironmentProbe(
        _environment_snapshot(control=True, alt=True)
    )
    gesture = _GestureProbe()
    screen = SimpleNamespace(
        _history_environment=environment,
        _history_gesture=gesture,
    )

    blocked = AgentsScreen._graph_flip_is_blocked(screen)  # type: ignore[arg-type]

    assert blocked
    assert environment.capture_calls == 1
    assert gesture.modifier_guarded == [True]


def test_input_environment_readiness_policy_rejects_non_owner_contexts() -> None:
    owner_window = SimpleNamespace(isActiveWindow=lambda: True)
    foreign_window = SimpleNamespace(isActiveWindow=lambda: True)
    owner = SimpleNamespace(
        isVisible=lambda: True,
        window=lambda: owner_window,
    )
    owner_focus = SimpleNamespace(window=lambda: owner_window)
    foreign_focus = SimpleNamespace(window=lambda: foreign_window)

    def app(*, modal=None, focus=None):
        return SimpleNamespace(
            activeModalWidget=lambda: modal,
            focusWidget=lambda: focus,
        )

    assert HistoryInputEnvironment._input_is_active(owner, app()) is True  # type: ignore[arg-type]
    assert (
        HistoryInputEnvironment._input_is_active(
            owner,
            app(focus=owner_focus),
        )
        is True
    )  # type: ignore[arg-type]
    assert (
        HistoryInputEnvironment._input_is_active(
            owner,
            app(focus=foreign_focus),
        )
        is False
    )  # type: ignore[arg-type]
    assert (
        HistoryInputEnvironment._input_is_active(
            owner,
            app(modal=object()),
        )
        is False
    )  # type: ignore[arg-type]

    hidden_owner = SimpleNamespace(
        isVisible=lambda: False,
        window=lambda: owner_window,
    )
    inactive_window = SimpleNamespace(isActiveWindow=lambda: False)
    inactive_owner = SimpleNamespace(
        isVisible=lambda: True,
        window=lambda: inactive_window,
    )
    assert HistoryInputEnvironment._input_is_active(hidden_owner, app()) is False  # type: ignore[arg-type]
    assert HistoryInputEnvironment._input_is_active(inactive_owner, app()) is False  # type: ignore[arg-type]
    assert HistoryInputEnvironment._input_is_active(owner, None) is False  # type: ignore[arg-type]

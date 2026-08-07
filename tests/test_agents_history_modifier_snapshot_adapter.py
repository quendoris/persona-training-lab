from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


class _GestureProbe:
    def __init__(self) -> None:
        self.modifier_guarded: list[bool] = []

    def flip_is_blocked(self, *, modifier_guarded: bool) -> bool:
        self.modifier_guarded.append(modifier_guarded)
        return modifier_guarded


def test_observed_modifiers_are_transport_facts_without_core_feedback() -> None:
    screen = SimpleNamespace(
        _queried_modifiers=lambda: (False, True),
    )
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Z,
        Qt.KeyboardModifier.ControlModifier,
        "z",
    )

    observed = AgentsScreen._observed_modifiers(screen, event)  # type: ignore[arg-type]

    assert observed == (True, True)


def test_graph_flip_guard_keeps_independent_modifier_snapshot_queries() -> None:
    queries: list[str] = []
    gesture = _GestureProbe()
    screen = SimpleNamespace(
        _queried_modifiers=lambda: (True, False),
        _queried_extra_history_modifiers=lambda: queries.append("extras") or False,
        _history_gesture=gesture,
    )

    blocked = AgentsScreen._graph_flip_is_blocked(screen)  # type: ignore[arg-type]

    assert blocked
    assert queries == ["extras"]
    assert gesture.modifier_guarded == [True]

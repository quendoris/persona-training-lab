from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QPointF

from persona_training_lab.ui.agents.screen_contextual import (
    AgentsScreen as ContextualAgentsScreen,
)


class _Bar:
    def __init__(self, value: int) -> None:
        self._value = value

    def value(self) -> int:
        return self._value


class _Scroll:
    def __init__(self, horizontal: int, vertical: int) -> None:
        self._horizontal = _Bar(horizontal)
        self._vertical = _Bar(vertical)

    def horizontalScrollBar(self) -> _Bar:
        return self._horizontal

    def verticalScrollBar(self) -> _Bar:
        return self._vertical


def test_contextual_adapter_delivers_fresh_pair_payload() -> None:
    delivered: list[tuple[str, dict[str, object]]] = []
    contexts = {
        "selected": {"model_version_id": "mdl_old"},
        "current": {"model_version_id": "mdl_current"},
    }
    window = SimpleNamespace(
        _go_to_screen_with_context=lambda key, payload: delivered.append(
            (key, payload)
        )
    )
    screen = SimpleNamespace(
        _selected_node_id="selected",
        _state=SimpleNamespace(current_node_id=lambda: "current"),
        _graph=SimpleNamespace(current_node_id=lambda: "fallback"),
        _context_for_node=lambda node_id: contexts[node_id],
        window=lambda: window,
    )

    ContextualAgentsScreen._open_workspace(screen, "analysis")
    contexts["selected"]["model_version_id"] = "mdl_mutated"

    assert delivered == [
        (
            "analysis",
            {
                "selected": {"model_version_id": "mdl_old"},
                "current": {"model_version_id": "mdl_current"},
            },
        )
    ]


def test_contextual_adapter_applies_pure_zoom_target() -> None:
    shifts: list[tuple[int, int]] = []
    screen = SimpleNamespace(
        _graph_scroll=_Scroll(120, 80),
        _apply_workspace_scroll_shift=lambda x, y: shifts.append((x, y)),
    )

    ContextualAgentsScreen._on_graph_zoom_anchor(
        screen,
        QPointF(200.0, 100.0),
        1.0,
        1.5,
    )

    assert shifts == [(220, 130)]


def test_contextual_adapter_ignores_invalid_previous_zoom() -> None:
    shifts: list[tuple[int, int]] = []
    screen = SimpleNamespace(
        _graph_scroll=_Scroll(10, 20),
        _apply_workspace_scroll_shift=lambda x, y: shifts.append((x, y)),
    )

    ContextualAgentsScreen._on_graph_zoom_anchor(
        screen,
        QPointF(100.0, 100.0),
        0.0,
        1.0,
    )

    assert shifts == []

from __future__ import annotations

from types import SimpleNamespace

import pytest

from persona_training_lab.ui.agents.screen_workspace_composition import (
    AgentsScreen,
)


class _StateSpy:
    def __init__(self) -> None:
        self.calls = 0

    def apply(self, _nodes):
        self.calls += 1
        return ()


class _StateCapture(_StateSpy):
    def apply(self, nodes):
        self.calls += 1
        return tuple(nodes)


class _GraphSpy:
    def __init__(self) -> None:
        self.set_nodes_calls = 0
        self.update_content_calls = 0

    def set_nodes(self, _nodes) -> None:
        self.set_nodes_calls += 1

    def update_node_content(self, _nodes) -> bool:
        self.update_content_calls += 1
        return True


def _screen_stub():
    state = _StateSpy()
    graph = _GraphSpy()

    def fail_reconciliation(_projection) -> None:
        raise RuntimeError("safety reconciliation failed")

    screen = SimpleNamespace(
        _selected_node_id="snapshot",
        _real_projection="previous-projection",
        _real_projection_signature=("previous-signature",),
        _lineage_nodes=("previous-node",),
        _state=state,
        _graph=graph,
        _reconcile_projection_resources=fail_reconciliation,
    )
    return screen, state, graph


def _projection():
    return SimpleNamespace(
        signature=("next-signature",),
        nodes=(),
        resources={},
    )


def test_full_projection_is_not_published_when_safety_reconciliation_fails() -> None:
    screen, state, graph = _screen_stub()

    with pytest.raises(RuntimeError, match="safety reconciliation failed"):
        AgentsScreen._apply_projection(screen, _projection())

    assert screen._real_projection == "previous-projection"
    assert screen._real_projection_signature == ("previous-signature",)
    assert screen._lineage_nodes == ("previous-node",)
    assert state.calls == 0
    assert graph.set_nodes_calls == 0


def test_content_projection_is_not_published_when_safety_reconciliation_fails() -> None:
    screen, state, graph = _screen_stub()
    result = SimpleNamespace(projection=_projection())

    with pytest.raises(RuntimeError, match="safety reconciliation failed"):
        AgentsScreen._apply_projection_content(screen, result)

    assert screen._real_projection == "previous-projection"
    assert screen._real_projection_signature == ("previous-signature",)
    assert screen._lineage_nodes == ("previous-node",)
    assert state.calls == 0
    assert graph.update_content_calls == 0

def test_local_rebuild_uses_only_screen_accepted_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accepted = SimpleNamespace(
        signature=("accepted-signature",),
        nodes=("accepted-node",),
    )
    unaccepted = SimpleNamespace(
        signature=("worker-signature",),
        nodes=("worker-node",),
    )
    state = _StateCapture()
    screen = SimpleNamespace(
        _lineage_refresh_coordinator=SimpleNamespace(
            last_good=SimpleNamespace(projection=unaccepted)
        ),
        _real_projection=accepted,
        _real_projection_signature=accepted.signature,
        _state=state,
    )
    monkeypatch.setattr(
        "persona_training_lab.ui.agents.screen_workspace_composition."
        "build_version_lineage",
        lambda nodes: nodes,
    )

    result = AgentsScreen._build_nodes(screen)

    assert result == ("accepted-node",)
    assert screen._real_projection is accepted
    assert screen._real_projection_signature == accepted.signature


def test_synchronous_projection_build_reconciles_before_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous = SimpleNamespace(
        signature=("previous-signature",),
        nodes=("previous-node",),
    )
    candidate = SimpleNamespace(
        signature=("candidate-signature",),
        nodes=("candidate-node",),
    )

    def fail_reconciliation(_projection) -> None:
        raise RuntimeError("safety reconciliation failed")

    screen = SimpleNamespace(
        _lineage_refresh_coordinator=None,
        _vm=object(),
        _real_projection=previous,
        _real_projection_signature=previous.signature,
        _state=_StateSpy(),
        _reconcile_projection_resources=fail_reconciliation,
    )
    monkeypatch.setattr(
        "persona_training_lab.ui.agents.screen_workspace_composition."
        "build_lineage_projection",
        lambda _vm: candidate,
    )

    with pytest.raises(RuntimeError, match="safety reconciliation failed"):
        AgentsScreen._build_nodes(screen)

    assert screen._real_projection is previous
    assert screen._real_projection_signature == previous.signature


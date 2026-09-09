from __future__ import annotations

from types import SimpleNamespace

import pytest

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.lineage_state import HistoryTransition
from persona_training_lab.ui.agents.screen_workspace_composition import AgentsScreen


def test_branch_creation_failure_never_selects_or_refreshes_unbound_child() -> None:
    calls: list[tuple[object, ...]] = []
    claims = (ResourceClaim("model_version", "mdl_1", "read"),)

    def fail_execute(parent_id: str, **kwargs) -> str:
        calls.append(("execute", parent_id, kwargs))
        raise RuntimeError("sqlite unavailable")

    screen = SimpleNamespace(
        _selected_node_id="snapshot",
        _runtime_claims_for_node=lambda node_id: (
            calls.append(("claims", node_id)) or claims
        ),
        _state=SimpleNamespace(
            is_custom_node=lambda node_id: (
                calls.append(("custom", node_id)) or False
            )
        ),
        _branch_creation_controller=SimpleNamespace(execute=fail_execute),
        _refresh_lineage=lambda *, center: calls.append(
            ("refresh_lineage", center)
        ),
        _refresh_runtime_safety=lambda *, force: calls.append(
            ("refresh_runtime", force)
        ),
    )

    with pytest.raises(RuntimeError, match="sqlite unavailable"):
        AgentsScreen._continue_from_selected(screen)

    assert screen._selected_node_id == "snapshot"
    assert [call[0] for call in calls] == ["claims", "custom", "execute"]
    execute_kwargs = calls[-1][2]
    assert isinstance(execute_kwargs, dict)
    assert execute_kwargs["parent_is_custom"] is False
    assert execute_kwargs["fallback_claims"] == claims


def test_branch_creation_is_exposed_only_after_controller_success() -> None:
    calls: list[tuple[object, ...]] = []
    claims = (ResourceClaim("artifact_path", "/models/one", "read"),)

    def execute(parent_id: str, **kwargs) -> str:
        calls.append(("execute", parent_id, kwargs))
        return "branch_002"

    screen = SimpleNamespace(
        _selected_node_id="branch_001",
        _runtime_claims_for_node=lambda node_id: (
            calls.append(("claims", node_id)) or claims
        ),
        _state=SimpleNamespace(
            is_custom_node=lambda node_id: (
                calls.append(("custom", node_id)) or True
            )
        ),
        _branch_creation_controller=SimpleNamespace(execute=execute),
        _refresh_lineage=lambda *, center: calls.append(
            ("refresh_lineage", center)
        ),
        _refresh_runtime_safety=lambda *, force: calls.append(
            ("refresh_runtime", force)
        ),
    )

    AgentsScreen._continue_from_selected(screen)

    assert screen._selected_node_id == "branch_002"
    assert [call[0] for call in calls] == [
        "claims",
        "custom",
        "execute",
        "refresh_lineage",
        "refresh_runtime",
    ]
    execute_kwargs = calls[2][2]
    assert isinstance(execute_kwargs, dict)
    assert execute_kwargs["parent_is_custom"] is True
    assert execute_kwargs["fallback_claims"] == claims
    assert calls[3] == ("refresh_lineage", True)
    assert calls[4] == ("refresh_runtime", True)


def test_protected_creation_toggle_routes_undo_before_ui_transition() -> None:
    calls: list[tuple[object, ...]] = []
    metadata = {"kind": "branch_create_v1", "child_node_id": "branch_001"}
    preview = SimpleNamespace(
        action_code="branch_create",
        direction="undo",
        metadata=metadata,
    )
    screen = SimpleNamespace(
        _state=SimpleNamespace(history_toggle_preview=lambda: preview),
        _branch_creation_controller=SimpleNamespace(
            supports_history=lambda value: value == metadata
        ),
        _close_canvas_menu=lambda: calls.append(("close_menu",)),
        _undo_branch_creation_history=lambda value: calls.append(
            ("undo_route", value)
        ),
        _redo_branch_creation_history=lambda value: calls.append(
            ("redo_route", value)
        ),
    )

    AgentsScreen._toggle_last_history_action(screen)

    assert calls == [("close_menu",), ("undo_route", preview)]


def test_protected_creation_undo_only_uses_creation_controller() -> None:
    calls: list[tuple[object, ...]] = []
    metadata = {"kind": "branch_create_v1", "child_node_id": "branch_001"}
    preview = SimpleNamespace(
        action_code="branch_create",
        direction="undo",
        metadata=metadata,
    )
    screen = SimpleNamespace(
        _state=SimpleNamespace(undo_preview=lambda: preview),
        _branch_creation_controller=SimpleNamespace(
            supports_history=lambda value: value == metadata
        ),
        _close_canvas_menu=lambda: calls.append(("close_menu",)),
        _undo_branch_creation_history=lambda value: calls.append(
            ("undo_route", value)
        ),
    )

    AgentsScreen._undo_history_only(screen)

    assert calls == [("close_menu",), ("undo_route", preview)]


def test_creation_history_undo_applies_ui_only_after_controller_success() -> None:
    calls: list[tuple[object, ...]] = []
    metadata = {"kind": "branch_create_v1", "child_node_id": "branch_001"}
    preview = SimpleNamespace(metadata=metadata)
    transition = HistoryTransition(
        action_code="branch_create",
        direction="undo",
        layout_snapshot={"schema": 1},
    )

    def undo_history(value, *, current_layout):
        calls.append(("controller", value, current_layout))
        return transition

    screen = SimpleNamespace(
        _branch_creation_controller=SimpleNamespace(undo_history=undo_history),
        _layout_snapshot=lambda: {"schema": 2},
        _apply_history_transition=lambda value: calls.append(
            ("apply", value)
        ),
        _refresh_runtime_safety=lambda *, force: calls.append(
            ("refresh", force)
        ),
        _sync_history_action=lambda: calls.append(("sync",)),
    )

    AgentsScreen._undo_branch_creation_history(screen, preview)

    assert calls == [
        ("controller", metadata, {"schema": 2}),
        ("apply", transition),
        ("refresh", True),
    ]


def test_creation_history_redo_failure_never_exposes_transition() -> None:
    calls: list[tuple[object, ...]] = []
    metadata = {"kind": "branch_create_v1", "child_node_id": "branch_001"}
    preview = SimpleNamespace(metadata=metadata)

    def fail_redo(value, *, current_layout):
        calls.append(("controller", value, current_layout))
        raise RuntimeError("sqlite unavailable")

    screen = SimpleNamespace(
        _branch_creation_controller=SimpleNamespace(redo_history=fail_redo),
        _layout_snapshot=lambda: {"schema": 2},
        _apply_history_transition=lambda value: calls.append(
            ("apply", value)
        ),
        _refresh_runtime_safety=lambda *, force: calls.append(
            ("refresh", force)
        ),
        _sync_history_action=lambda: calls.append(("sync",)),
    )

    with pytest.raises(RuntimeError, match="sqlite unavailable"):
        AgentsScreen._redo_branch_creation_history(screen, preview)

    assert calls == [("controller", metadata, {"schema": 2})]

from __future__ import annotations

from types import SimpleNamespace

import pytest

from persona_training_lab.application.runtime.operations import ResourceClaim
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

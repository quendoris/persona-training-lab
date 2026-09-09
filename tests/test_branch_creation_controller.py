from __future__ import annotations

from copy import deepcopy

import pytest

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.branch_creation import (
    BranchCreationController,
    BranchCreationExecutionError,
)


class _State:
    def __init__(self, *, fail_restore: bool = False) -> None:
        self.payload: dict[str, object] = {
            "custom_nodes": [],
            "current_node_id": "snapshot",
            "undo_stack": [],
        }
        self.fail_restore = fail_restore
        self.calls: list[tuple[object, ...]] = []

    def capture_transaction_state(self) -> dict[str, object]:
        snapshot = deepcopy(self.payload)
        self.calls.append(("capture", snapshot))
        return snapshot

    def continue_from(self, parent_id: str, layout_snapshot=None) -> str:
        child_id = "branch_001"
        self.calls.append(("continue", parent_id, layout_snapshot))
        self.payload["custom_nodes"] = [
            {"node_id": child_id, "parent_id": parent_id}
        ]
        self.payload["undo_stack"] = [
            {"action_code": "branch_create", "snapshot": "before"}
        ]
        return child_id

    def restore_transaction_state(self, snapshot: dict[str, object]) -> None:
        self.calls.append(("restore", deepcopy(snapshot)))
        if self.fail_restore:
            raise OSError("lineage restore unavailable")
        self.payload = deepcopy(snapshot)


class _Transactions:
    def __init__(self, *, bind_error: Exception | None = None) -> None:
        self.bind_error = bind_error
        self.calls: list[tuple[object, ...]] = []

    def bind_child(
        self,
        child_node_id: str,
        parent_node_id: str,
        *,
        parent_is_custom: bool,
        fallback_claims=(),
    ):
        claims = tuple(fallback_claims)
        self.calls.append(
            (
                "bind",
                child_node_id,
                parent_node_id,
                parent_is_custom,
                claims,
            )
        )
        if self.bind_error is not None:
            raise self.bind_error
        return claims


def _controller(
    state: _State,
    transactions: _Transactions,
) -> BranchCreationController:
    return BranchCreationController(
        state,  # type: ignore[arg-type]
        transactions,  # type: ignore[arg-type]
    )


def test_successful_creation_binds_safety_links_before_returning_child() -> None:
    state = _State()
    transactions = _Transactions()
    claims = (
        ResourceClaim("model_version", "mdl_1", "read"),
        ResourceClaim("dataset", "ds_1", "read"),
    )
    layout = {"schema": 1, "offsets": {"snapshot": {"x": 12}}}

    child_id = _controller(state, transactions).execute(
        "snapshot",
        parent_is_custom=False,
        fallback_claims=claims,
        layout_snapshot=layout,
    )

    assert child_id == "branch_001"
    assert state.payload["custom_nodes"] == [
        {"node_id": "branch_001", "parent_id": "snapshot"}
    ]
    assert transactions.calls == [
        ("bind", "branch_001", "snapshot", False, claims)
    ]
    assert tuple(call[0] for call in state.calls) == ("capture", "continue")


def test_link_binding_failure_restores_exact_precreation_state() -> None:
    state = _State()
    before = deepcopy(state.payload)
    transactions = _Transactions(bind_error=RuntimeError("sqlite unavailable"))
    claims = (ResourceClaim("model_version", "mdl_1", "read"),)

    with pytest.raises(RuntimeError, match="sqlite unavailable"):
        _controller(state, transactions).execute(
            "snapshot",
            parent_is_custom=False,
            fallback_claims=claims,
        )

    assert state.payload == before
    assert tuple(call[0] for call in state.calls) == (
        "capture",
        "continue",
        "restore",
    )
    assert transactions.calls == [
        ("bind", "branch_001", "snapshot", False, claims)
    ]


def test_custom_parent_mode_is_preserved_for_inherited_links() -> None:
    state = _State()
    transactions = _Transactions()
    claims = (ResourceClaim("artifact_path", "/models/one", "read"),)

    child_id = _controller(state, transactions).execute(
        "branch_000",
        parent_is_custom=True,
        fallback_claims=claims,
    )

    assert child_id == "branch_001"
    assert transactions.calls == [
        ("bind", "branch_001", "branch_000", True, claims)
    ]


def test_compensation_failure_preserves_original_and_restore_errors() -> None:
    state = _State(fail_restore=True)
    transactions = _Transactions(bind_error=RuntimeError("sqlite unavailable"))

    with pytest.raises(BranchCreationExecutionError) as captured:
        _controller(state, transactions).execute(
            "snapshot",
            parent_is_custom=False,
            fallback_claims=(),
        )

    error = captured.value
    assert isinstance(error.original_error, RuntimeError)
    assert str(error.original_error) == "sqlite unavailable"
    assert len(error.compensation_errors) == 1
    assert isinstance(error.compensation_errors[0], OSError)
    assert str(error.compensation_errors[0]) == "lineage restore unavailable"

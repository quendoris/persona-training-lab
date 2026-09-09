from __future__ import annotations

from copy import deepcopy

import pytest

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.branch_creation import (
    BranchCreationController,
    BranchCreationExecutionError,
)
from persona_training_lab.ui.agents.lineage_state import HistoryTransition


class _State:
    def __init__(
        self,
        *,
        fail_restore: bool = False,
        fail_attach: bool = False,
    ) -> None:
        self.payload: dict[str, object] = {
            "custom_nodes": [],
            "current_node_id": "snapshot",
            "undo_stack": [],
            "redo_stack": [],
        }
        self.fail_restore = fail_restore
        self.fail_attach = fail_attach
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
            {
                "action_code": "branch_create",
                "parent_id": parent_id,
                "snapshot": "before",
            }
        ]
        self.payload["redo_stack"] = []
        return child_id

    def restore_transaction_state(self, snapshot: dict[str, object]) -> None:
        self.calls.append(("restore", deepcopy(snapshot)))
        if self.fail_restore:
            raise OSError("lineage restore unavailable")
        self.payload = deepcopy(snapshot)

    def attach_latest_history_metadata(
        self,
        action_code: str,
        metadata: dict[str, object],
    ) -> None:
        self.calls.append(("attach", action_code, deepcopy(metadata)))
        if self.fail_attach:
            raise OSError("history metadata unavailable")
        stack = self.payload["undo_stack"]
        assert isinstance(stack, list) and stack
        entry = stack[-1]
        assert isinstance(entry, dict)
        assert entry["action_code"] == action_code
        entry["metadata"] = deepcopy(metadata)

    def undo_only(self, current_layout=None) -> HistoryTransition | None:
        self.calls.append(("undo", current_layout))
        undo_stack = self.payload["undo_stack"]
        redo_stack = self.payload["redo_stack"]
        assert isinstance(undo_stack, list)
        assert isinstance(redo_stack, list)
        if not undo_stack:
            return None
        entry = undo_stack.pop()
        assert isinstance(entry, dict)
        redo_stack.append(deepcopy(entry))
        self.payload["custom_nodes"] = []
        return HistoryTransition(
            action_code="branch_create",
            direction="undo",
            layout_snapshot=current_layout or {},
        )

    def redo_last_action(self, current_layout=None) -> HistoryTransition | None:
        self.calls.append(("redo", current_layout))
        undo_stack = self.payload["undo_stack"]
        redo_stack = self.payload["redo_stack"]
        assert isinstance(undo_stack, list)
        assert isinstance(redo_stack, list)
        if not redo_stack:
            return None
        entry = redo_stack.pop()
        assert isinstance(entry, dict)
        undo_stack.append(deepcopy(entry))
        parent_id = str(entry.get("parent_id", "snapshot"))
        self.payload["custom_nodes"] = [
            {"node_id": "branch_001", "parent_id": parent_id}
        ]
        return HistoryTransition(
            action_code="branch_create",
            direction="redo",
            layout_snapshot=current_layout or {},
        )


class _Transactions:
    def __init__(
        self,
        *,
        bind_error: Exception | None = None,
        forget_error: Exception | None = None,
        restore_links_error: Exception | None = None,
    ) -> None:
        self.bind_error = bind_error
        self.forget_error = forget_error
        self.restore_links_error = restore_links_error
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

    def capture_creation_history(self, child_node_id: str, claims):
        claim_tuple = tuple(claims)
        metadata = {
            "kind": "branch_create_v1",
            "child_node_id": child_node_id,
            "resource_links": [
                {
                    "resource_kind": claim.resource_kind,
                    "resource_id": claim.resource_id,
                    "access_mode": claim.access_mode,
                }
                for claim in claim_tuple
            ],
        }
        self.calls.append(("capture_history", child_node_id, claim_tuple))
        return metadata

    @staticmethod
    def creation_history_child(metadata) -> str:
        if metadata.get("kind") != "branch_create_v1":
            return ""
        return str(metadata.get("child_node_id", ""))

    def forget_creation_history(self, metadata) -> str:
        child_id = self.creation_history_child(metadata)
        self.calls.append(("forget_history", child_id))
        if self.forget_error is not None:
            raise self.forget_error
        return child_id

    def restore_creation_history(self, metadata) -> str:
        child_id = self.creation_history_child(metadata)
        self.calls.append(("restore_history", child_id))
        if self.restore_links_error is not None:
            raise self.restore_links_error
        return child_id

    def forget(self, node_ids) -> int:
        ids = tuple(node_ids)
        self.calls.append(("forget", ids))
        if self.forget_error is not None:
            raise self.forget_error
        return len(ids)


def _controller(
    state: _State,
    transactions: _Transactions,
) -> BranchCreationController:
    return BranchCreationController(
        state,  # type: ignore[arg-type]
        transactions,  # type: ignore[arg-type]
    )


def _creation_metadata(state: _State) -> dict[str, object]:
    stack = state.payload["undo_stack"]
    assert isinstance(stack, list) and stack
    entry = stack[-1]
    assert isinstance(entry, dict)
    metadata = entry.get("metadata")
    assert isinstance(metadata, dict)
    return metadata


def test_successful_creation_binds_links_and_persists_history_metadata() -> None:
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
    metadata = _creation_metadata(state)
    assert metadata == {
        "kind": "branch_create_v1",
        "child_node_id": "branch_001",
        "resource_links": [
            {
                "resource_kind": "model_version",
                "resource_id": "mdl_1",
                "access_mode": "read",
            },
            {
                "resource_kind": "dataset",
                "resource_id": "ds_1",
                "access_mode": "read",
            },
        ],
    }
    assert [call[0] for call in transactions.calls] == [
        "bind",
        "capture_history",
    ]
    assert [call[0] for call in state.calls] == [
        "capture",
        "continue",
        "attach",
    ]


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
    assert [call[0] for call in state.calls] == [
        "capture",
        "continue",
        "restore",
    ]
    assert [call[0] for call in transactions.calls] == ["bind"]


def test_metadata_persistence_failure_restores_state_then_forgets_links() -> None:
    state = _State(fail_attach=True)
    before = deepcopy(state.payload)
    transactions = _Transactions()
    claims = (ResourceClaim("model_version", "mdl_1", "read"),)

    with pytest.raises(OSError, match="history metadata unavailable"):
        _controller(state, transactions).execute(
            "snapshot",
            parent_is_custom=False,
            fallback_claims=claims,
        )

    assert state.payload == before
    assert [call[0] for call in state.calls] == [
        "capture",
        "continue",
        "attach",
        "restore",
    ]
    assert [call[0] for call in transactions.calls] == [
        "bind",
        "capture_history",
        "forget",
    ]
    assert transactions.calls[-1] == ("forget", ("branch_001",))


def test_failed_state_compensation_keeps_bound_safety_links() -> None:
    state = _State(fail_restore=True, fail_attach=True)
    transactions = _Transactions()

    with pytest.raises(BranchCreationExecutionError) as captured:
        _controller(state, transactions).execute(
            "snapshot",
            parent_is_custom=False,
            fallback_claims=(
                ResourceClaim("model_version", "mdl_1", "read"),
            ),
        )

    error = captured.value
    assert isinstance(error.original_error, OSError)
    assert str(error.original_error) == "history metadata unavailable"
    assert len(error.compensation_errors) == 1
    assert str(error.compensation_errors[0]) == "lineage restore unavailable"
    assert [call[0] for call in transactions.calls] == [
        "bind",
        "capture_history",
    ]
    assert state.payload["custom_nodes"] == [
        {"node_id": "branch_001", "parent_id": "snapshot"}
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
    assert transactions.calls[0] == (
        "bind",
        "branch_001",
        "branch_000",
        True,
        claims,
    )


def test_binding_failure_compensation_preserves_original_and_restore_errors() -> None:
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


def test_protected_undo_removes_state_and_safety_links() -> None:
    state = _State()
    transactions = _Transactions()
    controller = _controller(state, transactions)
    controller.execute(
        "snapshot",
        parent_is_custom=False,
        fallback_claims=(ResourceClaim("dataset", "ds_1", "read"),),
    )
    metadata = _creation_metadata(state)
    state.calls.clear()
    transactions.calls.clear()

    transition = controller.undo_history(
        metadata,
        current_layout={"schema": 1},
    )

    assert transition is not None
    assert transition.action_code == "branch_create"
    assert transition.direction == "undo"
    assert state.payload["custom_nodes"] == []
    assert [call[0] for call in state.calls] == ["capture", "undo"]
    assert transactions.calls == [("forget_history", "branch_001")]


def test_protected_undo_link_failure_restores_preundo_state() -> None:
    state = _State()
    transactions = _Transactions(forget_error=RuntimeError("sqlite unavailable"))
    controller = _controller(state, transactions)
    controller.execute(
        "snapshot",
        parent_is_custom=False,
        fallback_claims=(),
    )
    metadata = _creation_metadata(state)
    before = deepcopy(state.payload)
    state.calls.clear()

    with pytest.raises(RuntimeError, match="sqlite unavailable"):
        controller.undo_history(metadata)

    assert state.payload == before
    assert [call[0] for call in state.calls] == [
        "capture",
        "undo",
        "restore",
    ]


def test_protected_redo_restores_state_and_exact_safety_links() -> None:
    state = _State()
    transactions = _Transactions()
    controller = _controller(state, transactions)
    controller.execute(
        "snapshot",
        parent_is_custom=False,
        fallback_claims=(ResourceClaim("dataset", "ds_1", "read"),),
    )
    metadata = _creation_metadata(state)
    controller.undo_history(metadata)
    state.calls.clear()
    transactions.calls.clear()

    transition = controller.redo_history(
        metadata,
        current_layout={"schema": 1},
    )

    assert transition is not None
    assert transition.action_code == "branch_create"
    assert transition.direction == "redo"
    assert state.payload["custom_nodes"] == [
        {"node_id": "branch_001", "parent_id": "snapshot"}
    ]
    assert [call[0] for call in state.calls] == ["capture", "redo"]
    assert transactions.calls == [("restore_history", "branch_001")]


def test_protected_redo_link_failure_restores_preredo_state() -> None:
    state = _State()
    transactions = _Transactions()
    controller = _controller(state, transactions)
    controller.execute(
        "snapshot",
        parent_is_custom=False,
        fallback_claims=(),
    )
    metadata = _creation_metadata(state)
    controller.undo_history(metadata)
    before = deepcopy(state.payload)
    transactions.restore_links_error = RuntimeError("sqlite unavailable")
    state.calls.clear()

    with pytest.raises(RuntimeError, match="sqlite unavailable"):
        controller.redo_history(metadata)

    assert state.payload == before
    assert [call[0] for call in state.calls] == [
        "capture",
        "redo",
        "restore",
    ]

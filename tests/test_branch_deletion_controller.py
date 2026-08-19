from __future__ import annotations

from copy import deepcopy

import pytest

from persona_training_lab.application.runtime.operations import (
    OperationBlocker,
    OperationConflictError,
    ResourceClaim,
    RuntimeOperation,
)
from persona_training_lab.ui.agents.branch_deletion import (
    BranchDeletionCommittedError,
    BranchDeletionController,
    BranchDeletionStatus,
)
from persona_training_lab.ui.agents.runtime_policy import (
    LineageBranchTransactions,
)


class _State:
    def __init__(self) -> None:
        self.ids = ("branch_001", "branch_002")
        self.restored: list[dict[str, object]] = []
        self.deleted: list[tuple[str, object]] = []

    def custom_subtree_ids(self, _node_id: str) -> tuple[str, ...]:
        return self.ids

    def capture_transaction_state(self) -> dict[str, object]:
        return {"ids": self.ids}

    def restore_transaction_state(self, snapshot: dict[str, object]) -> None:
        self.restored.append(deepcopy(snapshot))
        self.ids = tuple(snapshot["ids"])  # type: ignore[arg-type]

    def delete_subtree(self, node_id: str, layout_snapshot=None):
        self.deleted.append((node_id, layout_snapshot))
        removed = self.ids
        self.ids = ()
        return removed


class _Lease:
    def __init__(self, *, fail_succeed: bool = False) -> None:
        self.fail_succeed = fail_succeed
        self.calls: list[tuple[str, str]] = []

    def succeed(self) -> bool:
        self.calls.append(("succeed", ""))
        if self.fail_succeed:
            raise RuntimeError("lease finalization failed")
        return True

    def fail(self, message: str) -> bool:
        self.calls.append(("fail", message))
        return True

    def cancel(self, message: str = "") -> bool:
        self.calls.append(("cancel", message))
        return True


class _Safety:
    def __init__(self, lease: _Lease | None = None) -> None:
        self.lease = lease or _Lease()
        self.calls: list[tuple[object, ...]] = []
        self.forget_error: Exception | None = None
        self.conflict: OperationBlocker | None = None

    def begin_deletion(self, node_ids, *, subject_id):
        self.calls.append(("begin", tuple(node_ids), subject_id))
        if self.conflict is not None:
            raise OperationConflictError((self.conflict,))
        return self.lease

    def links_for_node(self, _node_id: str) -> tuple[ResourceClaim, ...]:
        return ()

    def forget_nodes(self, node_ids):
        self.calls.append(("forget", tuple(node_ids)))
        if self.forget_error is not None:
            raise self.forget_error
        return len(tuple(node_ids))


def _controller(
    state: _State,
    safety: _Safety,
) -> BranchDeletionController:
    transactions = LineageBranchTransactions(safety)  # type: ignore[arg-type]
    return BranchDeletionController(state, transactions)  # type: ignore[arg-type]


def _plan(controller: BranchDeletionController):
    plan = controller.prepare(
        "branch_001",
        node_title="Experiment",
        parent_id="snapshot",
        graph_current_id="base",
    )
    assert plan is not None
    return plan


def test_deletion_plan_is_semantic_and_uses_parent_fallback() -> None:
    state = _State()
    controller = _controller(state, _Safety())

    plan = _plan(controller)

    assert plan.node_id == "branch_001"
    assert plan.node_title == "Experiment"
    assert plan.removed_ids == ("branch_001", "branch_002")
    assert plan.descendant_count == 1
    assert plan.fallback_id == "snapshot"


def test_stale_plan_never_opens_runtime_lease() -> None:
    state = _State()
    safety = _Safety()
    controller = _controller(state, safety)
    plan = _plan(controller)
    state.ids = ("branch_001", "branch_003")

    result = controller.execute(plan)

    assert result.status is BranchDeletionStatus.STALE
    assert state.deleted == []
    assert safety.calls == []


def test_active_operation_returns_blockers_without_state_mutation() -> None:
    operation = RuntimeOperation(
        operation_id="op_1",
        operation_kind="training",
        subject_kind="training_run",
        subject_id="trn_1",
        state="running",
        correlation_id="corr_1",
        owner_pid=1,
        started_at="now",
        heartbeat_at="now",
    )
    blocker = OperationBlocker(
        operation,
        ResourceClaim("model_version", "mdl_1", "write"),
    )
    state = _State()
    safety = _Safety()
    safety.conflict = blocker
    controller = _controller(state, safety)

    result = controller.execute(_plan(controller))

    assert result.status is BranchDeletionStatus.BLOCKED
    assert result.blockers == (blocker,)
    assert state.deleted == []
    assert state.restored == []


def test_successful_deletion_commits_state_links_and_lease() -> None:
    state = _State()
    safety = _Safety()
    controller = _controller(state, safety)
    layout = {"schema": 1, "offsets": {"branch_001": {"x": 2}}}

    result = controller.execute(_plan(controller), layout_snapshot=layout)

    assert result.status is BranchDeletionStatus.DELETED
    assert result.removed_ids == ("branch_001", "branch_002")
    assert result.fallback_id == "snapshot"
    assert state.ids == ()
    assert state.deleted == [("branch_001", layout)]
    assert safety.calls == [
        ("begin", ("branch_001", "branch_002"), "branch_001"),
        ("forget", ("branch_001", "branch_002")),
    ]
    assert safety.lease.calls == [("succeed", "")]


def test_link_cleanup_failure_restores_exact_state_and_fails_lease() -> None:
    state = _State()
    safety = _Safety()
    safety.forget_error = RuntimeError("sqlite unavailable")
    controller = _controller(state, safety)

    with pytest.raises(RuntimeError, match="sqlite unavailable"):
        controller.execute(_plan(controller))

    assert state.ids == ("branch_001", "branch_002")
    assert state.restored == [
        {"ids": ("branch_001", "branch_002")}
    ]
    assert safety.lease.calls == [("fail", "sqlite unavailable")]


def test_lease_finalization_failure_reports_committed_deletion() -> None:
    state = _State()
    lease = _Lease(fail_succeed=True)
    safety = _Safety(lease)
    controller = _controller(state, safety)

    with pytest.raises(BranchDeletionCommittedError) as captured:
        controller.execute(_plan(controller))

    assert captured.value.result.status is BranchDeletionStatus.DELETED
    assert captured.value.result.removed_ids == (
        "branch_001",
        "branch_002",
    )
    assert state.ids == ()
    assert state.restored == []
    assert lease.calls == [("succeed", "")]

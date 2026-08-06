from __future__ import annotations

from types import SimpleNamespace

import pytest

from persona_training_lab.ui.agents.branch_deletion import (
    BranchDeletionCommittedError,
    BranchDeletionController,
    BranchDeletionExecutionError,
)


class _State:
    def __init__(self, *, delete_error: Exception | None = None) -> None:
        self.ids = ("branch_001",)
        self.delete_error = delete_error

    def custom_subtree_ids(self, _node_id: str):
        return self.ids

    def capture_transaction_state(self):
        return {"ids": self.ids}

    def restore_transaction_state(self, snapshot):
        self.ids = tuple(snapshot["ids"])

    def delete_subtree(self, _node_id: str, _layout_snapshot=None):
        if self.delete_error is not None:
            raise self.delete_error
        removed = self.ids
        self.ids = ()
        return removed


class _Lease:
    def __init__(self, *, succeed=True, fail=True) -> None:
        self.succeed_result = succeed
        self.fail_result = fail

    def succeed(self):
        return self.succeed_result

    def fail(self, _message: str):
        return self.fail_result

    def cancel(self, _message: str = ""):
        return True


class _Transactions:
    def __init__(self, lease: _Lease) -> None:
        self.lease = lease

    def begin_deletion(self, _node_ids, *, subject_id: str):
        assert subject_id == "branch_001"
        return self.lease

    def forget(self, _node_ids):
        return 1


def _plan(controller: BranchDeletionController):
    plan = controller.prepare(
        "branch_001",
        node_title="Branch",
        parent_id="snapshot",
        graph_current_id="base",
    )
    assert plan is not None
    return plan


def test_false_success_result_is_a_committed_finalization_error() -> None:
    state = _State()
    controller = BranchDeletionController(
        state,  # type: ignore[arg-type]
        _Transactions(_Lease(succeed=False)),  # type: ignore[arg-type]
    )

    with pytest.raises(BranchDeletionCommittedError) as captured:
        controller.execute(_plan(controller))

    assert state.ids == ()
    assert isinstance(captured.value.finalization_error, RuntimeError)
    assert "not finalized" in str(captured.value.finalization_error)


def test_false_failure_result_cannot_hide_unclosed_lease() -> None:
    original = OSError("state write failed")
    state = _State(delete_error=original)
    controller = BranchDeletionController(
        state,  # type: ignore[arg-type]
        _Transactions(_Lease(fail=False)),  # type: ignore[arg-type]
    )

    with pytest.raises(BranchDeletionExecutionError) as captured:
        controller.execute(_plan(controller))

    assert captured.value.original_error is original
    assert len(captured.value.compensation_errors) == 1
    assert isinstance(
        captured.value.compensation_errors[0],
        RuntimeError,
    )

from __future__ import annotations

from types import SimpleNamespace

import pytest

from persona_training_lab.ui.agents.branch_deletion import (
    BranchDeletionCommittedError,
    BranchDeletionPlan,
    BranchDeletionResult,
    BranchDeletionStatus,
)
from persona_training_lab.ui.agents.screen_contextual import (
    AgentsScreen as ContextualAgentsScreen,
)


_PLAN = BranchDeletionPlan(
    node_id="branch_001",
    node_title="Branch",
    removed_ids=("branch_001", "branch_002"),
    fallback_id="snapshot",
)


class _Controller:
    def __init__(self, outcome) -> None:
        self.outcome = outcome
        self.executed: list[tuple[object, object]] = []

    def prepare(self, *args, **kwargs):
        return _PLAN

    def execute(self, plan, *, layout_snapshot=None):
        self.executed.append((plan, layout_snapshot))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def _screen(controller: _Controller):
    applied: list[BranchDeletionResult] = []
    blockers: list[object] = []
    refreshes: list[bool] = []
    screen = SimpleNamespace(
        _lineage_runtime_safety=object(),
        _node_by_id=lambda _node_id: SimpleNamespace(
            title="Branch",
            parent_id="snapshot",
        ),
        _render_text=lambda value: value,
        _text=lambda key, **_values: key,
        _graph=SimpleNamespace(current_node_id=lambda: "snapshot"),
        _branch_deletion_controller=controller,
        _confirm_branch_deletion=lambda _title, _detail: True,
        _layout_snapshot=lambda: {"schema": 1},
        _show_runtime_blockers=lambda values: blockers.extend(values),
        _apply_branch_deletion_result=applied.append,
        _refresh_lineage=lambda *, center: refreshes.append(center),
    )
    return screen, applied, blockers, refreshes


def test_blocked_deletion_renders_blockers_without_applying_state() -> None:
    blocker = SimpleNamespace(message="training holds model")
    result = BranchDeletionResult(
        BranchDeletionStatus.BLOCKED,
        blockers=(blocker,),  # type: ignore[arg-type]
    )
    controller = _Controller(result)
    screen, applied, blockers, refreshes = _screen(controller)

    ContextualAgentsScreen._delete_local_branch_subtree(  # type: ignore[arg-type]
        screen,
        "branch_001",
    )

    assert blockers == [blocker]
    assert applied == []
    assert refreshes == []


def test_stale_deletion_refreshes_without_applying_committed_result() -> None:
    controller = _Controller(
        BranchDeletionResult(
            BranchDeletionStatus.STALE,
            removed_ids=("branch_001", "branch_003"),
            fallback_id="snapshot",
        )
    )
    screen, applied, blockers, refreshes = _screen(controller)

    ContextualAgentsScreen._delete_local_branch_subtree(  # type: ignore[arg-type]
        screen,
        "branch_001",
    )

    assert applied == []
    assert blockers == []
    assert refreshes == [False]


def test_committed_finalization_error_updates_ui_before_propagating() -> None:
    committed = BranchDeletionResult(
        BranchDeletionStatus.DELETED,
        removed_ids=_PLAN.removed_ids,
        fallback_id="snapshot",
    )
    error = BranchDeletionCommittedError(
        committed,
        RuntimeError("lease finalization failed"),
    )
    controller = _Controller(error)
    screen, applied, blockers, refreshes = _screen(controller)

    with pytest.raises(BranchDeletionCommittedError) as captured:
        ContextualAgentsScreen._delete_local_branch_subtree(  # type: ignore[arg-type]
            screen,
            "branch_001",
        )

    assert captured.value is error
    assert applied == [committed]
    assert blockers == []
    assert refreshes == []

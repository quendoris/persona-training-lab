from __future__ import annotations

import sqlite3

import pytest

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.atomic import (
    RuntimeOperationCoordinator,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.infrastructure.persistence.repositories.lineage_resource_links import (
    SQLiteLineageResourceLinksRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.runtime_operations_atomic import (
    SQLiteRuntimeOperationsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.agents.branch_deletion import (
    BranchDeletionController,
    BranchDeletionStatus,
)
from persona_training_lab.ui.agents.lineage_state_atomic import (
    AtomicLineageStateStore,
)
from persona_training_lab.ui.agents.runtime_policy import LineageBranchTransactions


def _connect(path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=2.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 2000")
    return connection


def _build_deleted_branch(tmp_path, *, database_name: str = "runtime.sqlite3"):
    connection = _connect(tmp_path / database_name)
    create_minimal_schema(connection)
    operations = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(connection)
    )
    safety = LineageRuntimeSafety(
        SQLiteLineageResourceLinksRepository(connection),
        operations,
    )
    transactions = LineageBranchTransactions(safety)
    state = AtomicLineageStateStore(
        tmp_path / f"{database_name}.lineage-state.json"
    )
    branch_id = state.continue_from("snapshot")
    expected_links = (
        ResourceClaim("model_version", "mdl_recorded", "read"),
        ResourceClaim("artifact_path", "/models/mdl_recorded", "read"),
    )
    safety.bind_node(branch_id, expected_links)

    controller = BranchDeletionController(state, transactions)
    plan = controller.prepare(
        branch_id,
        node_title="Branch",
        parent_id="snapshot",
        graph_current_id="snapshot",
    )
    assert plan is not None
    assert controller.execute(plan).status is BranchDeletionStatus.DELETED
    assert state.is_custom_node(branch_id) is False
    assert safety.links_for_node(branch_id) == ()
    return (
        connection,
        safety,
        transactions,
        state,
        controller,
        branch_id,
        tuple(sorted(expected_links)),
    )


def _restore_deleted_branch_for_redo(tmp_path):
    (
        connection,
        safety,
        transactions,
        state,
        controller,
        branch_id,
        expected_links,
    ) = _build_deleted_branch(tmp_path)

    undo_preview = state.undo_preview()
    assert undo_preview is not None
    assert undo_preview.action_code == "branch_delete"
    restored_ids = transactions.restore_deletion_history(undo_preview.metadata)
    assert restored_ids == (branch_id,)
    undo_transition = state.undo_only()
    assert undo_transition is not None
    assert undo_transition.action_code == "branch_delete"
    assert undo_transition.direction == "undo"
    assert state.is_custom_node(branch_id) is True

    redo_preview = state.history_toggle_preview()
    assert redo_preview is not None
    assert redo_preview.action_code == "branch_delete"
    assert redo_preview.direction == "redo"
    redo_plan = controller.prepare(
        branch_id,
        node_title="Branch",
        parent_id="snapshot",
        graph_current_id="snapshot",
    )
    assert redo_plan is not None
    return (
        connection,
        safety,
        transactions,
        state,
        controller,
        redo_plan,
        branch_id,
        expected_links,
    )


def test_delete_undo_refuses_foreign_links_for_recorded_deleted_nodes(
    tmp_path,
) -> None:
    (
        connection,
        safety,
        transactions,
        state,
        _controller,
        branch_id,
        _expected_links,
    ) = _build_deleted_branch(tmp_path, database_name="runtime-undo.sqlite3")
    preview = state.undo_preview()
    assert preview is not None
    drifted_links = (
        ResourceClaim("dataset", "ds_foreign", "read"),
    )
    safety.bind_node(branch_id, drifted_links)

    with pytest.raises(RuntimeError, match="safety identity is not empty"):
        transactions.restore_deletion_history(preview.metadata)

    assert state.is_custom_node(branch_id) is False
    assert safety.links_for_node(branch_id) == drifted_links
    pending = state.undo_preview()
    assert pending is not None
    assert pending.action_code == "branch_delete"
    assert pending.direction == "undo"
    connection.close()


def test_delete_redo_refuses_links_that_drifted_from_recorded_history(
    tmp_path,
) -> None:
    (
        connection,
        safety,
        _transactions,
        state,
        controller,
        plan,
        branch_id,
        _expected_links,
    ) = _restore_deleted_branch_for_redo(tmp_path)
    drifted_links = (
        ResourceClaim("model_version", "mdl_other", "read"),
    )
    safety.bind_node(branch_id, drifted_links)

    result = controller.execute_history_redo(plan)

    assert result.status is BranchDeletionStatus.STALE
    assert state.is_custom_node(branch_id) is True
    assert safety.links_for_node(branch_id) == drifted_links
    pending = state.history_toggle_preview()
    assert pending is not None
    assert pending.action_code == "branch_delete"
    assert pending.direction == "redo"
    connection.close()


class _DriftingDeletionTransactions(LineageBranchTransactions):
    def __init__(
        self,
        safety: LineageRuntimeSafety,
        *,
        branch_id: str,
        drifted_links: tuple[ResourceClaim, ...],
    ) -> None:
        super().__init__(safety)
        self._test_safety = safety
        self._branch_id = branch_id
        self._drifted_links = drifted_links

    def begin_deletion(self, node_ids, *, subject_id):
        lease = super().begin_deletion(node_ids, subject_id=subject_id)
        self._test_safety.bind_node(self._branch_id, self._drifted_links)
        return lease


def test_delete_redo_rechecks_links_after_runtime_guard_acquisition(
    tmp_path,
) -> None:
    (
        connection,
        safety,
        _transactions,
        state,
        _controller,
        plan,
        branch_id,
        expected_links,
    ) = _restore_deleted_branch_for_redo(tmp_path)
    assert safety.links_for_node(branch_id) == expected_links

    drifted_links = (
        ResourceClaim("dataset", "ds_changed", "read"),
    )
    drifting_transactions = _DriftingDeletionTransactions(
        safety,
        branch_id=branch_id,
        drifted_links=drifted_links,
    )
    controller = BranchDeletionController(state, drifting_transactions)

    result = controller.execute_history_redo(plan)

    assert result.status is BranchDeletionStatus.STALE
    assert state.is_custom_node(branch_id) is True
    assert safety.links_for_node(branch_id) == drifted_links
    pending = state.history_toggle_preview()
    assert pending is not None
    assert pending.action_code == "branch_delete"
    assert pending.direction == "redo"
    connection.close()

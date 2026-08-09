from __future__ import annotations

import sqlite3

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


def test_active_training_blocks_durable_branch_deletion_without_partial_state(
    tmp_path,
) -> None:
    database_path = tmp_path / "runtime.sqlite3"
    training_connection = _connect(database_path)
    create_minimal_schema(training_connection)
    deletion_connection = _connect(database_path)

    training_operations = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(training_connection)
    )
    deletion_operations = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(deletion_connection)
    )
    safety = LineageRuntimeSafety(
        SQLiteLineageResourceLinksRepository(deletion_connection),
        deletion_operations,
    )

    state_path = tmp_path / "lineage-state.json"
    state = AtomicLineageStateStore(state_path)
    branch_id = state.continue_from(
        "snapshot",
        layout_snapshot={"schema": 1, "phase": "before-branch"},
    )
    child_id = state.continue_from(
        branch_id,
        layout_snapshot={"schema": 1, "phase": "before-child"},
    )
    linked_resources = (
        ResourceClaim("model_version", "mdl_001", "read"),
        ResourceClaim("artifact_path", "/models/mdl_001", "read"),
    )
    safety.bind_node(branch_id, linked_resources)
    safety.inherit_node(child_id, branch_id)

    controller = BranchDeletionController(
        state,
        LineageBranchTransactions(safety),
    )
    plan = controller.prepare(
        branch_id,
        node_title="Training branch",
        parent_id="snapshot",
        graph_current_id="snapshot",
    )
    assert plan is not None
    assert plan.removed_ids == (branch_id, child_id)

    deletion_layout = {
        "schema": 1,
        "offsets": {
            branch_id: {"x": 20, "y": -4},
            child_id: {"x": 42, "y": 8},
        },
    }
    payload_before = state.capture_transaction_state()
    bytes_before = state_path.read_bytes()
    branch_links_before = safety.links_for_node(branch_id)
    child_links_before = safety.links_for_node(child_id)

    training = training_operations.begin(
        operation_kind="training",
        subject_kind="training_run",
        subject_id="trn_001",
        claims=(
            ResourceClaim("model_version", "mdl_001", "read"),
            ResourceClaim("artifact_path", "/models/mdl_001", "write"),
        ),
    )

    blocked = controller.execute(plan, layout_snapshot=deletion_layout)

    assert blocked.status is BranchDeletionStatus.BLOCKED
    assert blocked.removed_ids == ()
    assert blocked.fallback_id == ""
    assert blocked.blockers
    assert {item.operation.operation_id for item in blocked.blockers} == {
        training.operation_id
    }
    assert state.capture_transaction_state() == payload_before
    assert state_path.read_bytes() == bytes_before
    assert state.custom_subtree_ids(branch_id) == (branch_id, child_id)
    assert safety.links_for_node(branch_id) == branch_links_before
    assert safety.links_for_node(child_id) == child_links_before
    assert tuple(
        (row["operation_kind"], row["state"])
        for row in deletion_connection.execute(
            "SELECT operation_kind, state FROM runtime_operations ORDER BY id"
        ).fetchall()
    ) == (("training", "running"),)

    assert training.succeed() is True
    assert deletion_operations.active_operations() == ()

    deleted = controller.execute(plan, layout_snapshot=deletion_layout)

    assert deleted.status is BranchDeletionStatus.DELETED
    assert deleted.removed_ids == (branch_id, child_id)
    assert deleted.fallback_id == "snapshot"
    assert state.custom_subtree_ids(branch_id) == ()
    assert safety.links_for_node(branch_id) == ()
    assert safety.links_for_node(child_id) == ()
    assert deletion_operations.active_operations() == ()
    assert state_path.read_bytes() != bytes_before

    reloaded = AtomicLineageStateStore(state_path)
    assert reloaded.custom_subtree_ids(branch_id) == ()
    assert reloaded.is_custom_node(branch_id) is False
    assert reloaded.is_custom_node(child_id) is False

    operation_rows = tuple(
        (row["operation_kind"], row["state"])
        for row in deletion_connection.execute(
            "SELECT operation_kind, state FROM runtime_operations "
            "ORDER BY started_at, id"
        ).fetchall()
    )
    assert operation_rows == (
        ("training", "succeeded"),
        ("lineage_delete", "succeeded"),
    )

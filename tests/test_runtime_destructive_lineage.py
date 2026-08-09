from __future__ import annotations

import sqlite3
from queue import Queue
from threading import Barrier, Event, Thread

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.atomic import (
    RuntimeOperationCoordinator,
)
from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
)
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


def test_training_and_branch_deletion_race_has_exactly_one_winner(tmp_path) -> None:
    database_path = tmp_path / "runtime-race.sqlite3"
    setup_connection = _connect(database_path)
    create_minimal_schema(setup_connection)
    setup_operations = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(setup_connection)
    )
    setup_safety = LineageRuntimeSafety(
        SQLiteLineageResourceLinksRepository(setup_connection),
        setup_operations,
    )

    state_path = tmp_path / "lineage-race.json"
    setup_state = AtomicLineageStateStore(state_path)
    branch_id = setup_state.continue_from("snapshot")
    child_id = setup_state.continue_from(branch_id)
    linked_resources = (
        ResourceClaim("model_version", "mdl_race", "read"),
        ResourceClaim("artifact_path", "/models/race", "read"),
    )
    setup_safety.bind_node(branch_id, linked_resources)
    setup_safety.inherit_node(child_id, branch_id)
    plan = BranchDeletionController(
        setup_state,
        LineageBranchTransactions(setup_safety),
    ).prepare(
        branch_id,
        node_title="Race branch",
        parent_id="snapshot",
        graph_current_id="snapshot",
    )
    assert plan is not None
    assert plan.removed_ids == (branch_id, child_id)

    bytes_before = state_path.read_bytes()
    payload_before = setup_state.capture_transaction_state()
    links_before = {
        branch_id: setup_safety.links_for_node(branch_id),
        child_id: setup_safety.links_for_node(child_id),
    }
    setup_connection.close()

    start = Barrier(3)
    training_attempted = Event()
    deletion_finished = Event()
    outcomes: Queue[tuple[str, object]] = Queue()

    class _PausingState(AtomicLineageStateStore):
        def capture_transaction_state(self):
            training_attempted.wait(timeout=5)
            return super().capture_transaction_state()

    def run_training() -> None:
        connection = _connect(database_path)
        operations = RuntimeOperationCoordinator(
            SQLiteRuntimeOperationsRepository(connection)
        )
        start.wait(timeout=5)
        try:
            lease = operations.begin(
                operation_kind="training",
                subject_kind="training_run",
                subject_id="trn_race",
                claims=(
                    ResourceClaim("model_version", "mdl_race", "read"),
                    ResourceClaim("artifact_path", "/models/race", "write"),
                ),
            )
        except OperationConflictError as error:
            outcomes.put(("training_blocked", error))
            training_attempted.set()
        except BaseException as error:
            outcomes.put(("training_error", error))
            training_attempted.set()
        else:
            outcomes.put(("training_won", lease.operation_id))
            training_attempted.set()
            if not deletion_finished.wait(timeout=5):
                outcomes.put(
                    ("training_error", RuntimeError("deletion thread timed out"))
                )
            lease.succeed()
        finally:
            connection.close()

    def run_deletion() -> None:
        connection = _connect(database_path)
        operations = RuntimeOperationCoordinator(
            SQLiteRuntimeOperationsRepository(connection)
        )
        safety = LineageRuntimeSafety(
            SQLiteLineageResourceLinksRepository(connection),
            operations,
        )
        state = _PausingState(state_path)
        controller = BranchDeletionController(
            state,
            LineageBranchTransactions(safety),
        )
        start.wait(timeout=5)
        try:
            result = controller.execute(
                plan,
                layout_snapshot={"schema": 1, "race": True},
            )
            outcomes.put(("deletion_result", result))
        except BaseException as error:
            outcomes.put(("deletion_error", error))
        finally:
            deletion_finished.set()
            connection.close()

    training_thread = Thread(target=run_training, daemon=True)
    deletion_thread = Thread(target=run_deletion, daemon=True)
    training_thread.start()
    deletion_thread.start()
    start.wait(timeout=5)
    training_thread.join(timeout=10)
    deletion_thread.join(timeout=10)

    assert training_thread.is_alive() is False
    assert deletion_thread.is_alive() is False

    observed: dict[str, object] = {}
    while not outcomes.empty():
        key, value = outcomes.get_nowait()
        assert key not in observed
        observed[key] = value
    assert "training_error" not in observed
    assert "deletion_error" not in observed
    assert "deletion_result" in observed

    deletion_result = observed["deletion_result"]
    verification_connection = _connect(database_path)
    verification_operations = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(verification_connection)
    )
    verification_safety = LineageRuntimeSafety(
        SQLiteLineageResourceLinksRepository(verification_connection),
        verification_operations,
    )
    reloaded = AtomicLineageStateStore(state_path)

    if "training_won" in observed:
        assert "training_blocked" not in observed
        assert deletion_result.status is BranchDeletionStatus.BLOCKED
        assert reloaded.capture_transaction_state() == payload_before
        assert state_path.read_bytes() == bytes_before
        assert reloaded.custom_subtree_ids(branch_id) == (branch_id, child_id)
        assert verification_safety.links_for_node(branch_id) == links_before[branch_id]
        assert verification_safety.links_for_node(child_id) == links_before[child_id]
        operation_rows = tuple(
            (row["operation_kind"], row["state"])
            for row in verification_connection.execute(
                "SELECT operation_kind, state FROM runtime_operations ORDER BY id"
            ).fetchall()
        )
        assert operation_rows == (("training", "succeeded"),)
    else:
        assert "training_blocked" in observed
        assert isinstance(observed["training_blocked"], OperationConflictError)
        assert deletion_result.status is BranchDeletionStatus.DELETED
        assert deletion_result.removed_ids == (branch_id, child_id)
        assert reloaded.custom_subtree_ids(branch_id) == ()
        assert verification_safety.links_for_node(branch_id) == ()
        assert verification_safety.links_for_node(child_id) == ()
        operation_rows = tuple(
            (row["operation_kind"], row["state"])
            for row in verification_connection.execute(
                "SELECT operation_kind, state FROM runtime_operations ORDER BY id"
            ).fetchall()
        )
        assert operation_rows == (("lineage_delete", "succeeded"),)

    assert verification_operations.active_operations() == ()
    verification_connection.close()

from __future__ import annotations

import sqlite3

import pytest

from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
    RuntimeOperationCoordinator,
)
from persona_training_lab.infrastructure.persistence.repositories.runtime_operations import (
    SQLiteRuntimeOperationsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


def _coordinator() -> tuple[
    sqlite3.Connection,
    RuntimeOperationCoordinator,
]:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_minimal_schema(connection)
    repository = SQLiteRuntimeOperationsRepository(connection)
    return connection, RuntimeOperationCoordinator(repository)


def test_concurrent_read_operations_are_allowed() -> None:
    _connection, coordinator = _coordinator()
    resource = ResourceClaim("model_version", "mdl_001", "read")

    first = coordinator.begin(
        operation_kind="personality_test",
        subject_kind="experiment",
        subject_id="evr_001",
        claims=(resource,),
    )
    second = coordinator.begin(
        operation_kind="comparison",
        subject_kind="analysis",
        subject_id="anl_001",
        claims=(resource,),
    )

    assert len(coordinator.active_operations()) == 2
    assert first.succeed() is True
    assert second.succeed() is True
    assert coordinator.active_operations() == ()


def test_write_claim_conflicts_with_active_reader() -> None:
    _connection, coordinator = _coordinator()
    reader = coordinator.begin(
        operation_kind="personality_test",
        subject_kind="experiment",
        subject_id="evr_001",
        claims=(ResourceClaim("artifact_path", "/models/one", "read"),),
    )

    with pytest.raises(OperationConflictError) as captured:
        coordinator.begin(
            operation_kind="training",
            subject_kind="training_run",
            subject_id="trn_001",
            claims=(ResourceClaim("artifact_path", "/models/one", "write"),),
        )

    assert captured.value.blockers[0].operation.operation_id == reader.operation_id
    assert reader.cancel("test cleanup") is True


def test_deletion_is_blocked_even_by_read_claim() -> None:
    _connection, coordinator = _coordinator()
    lease = coordinator.begin(
        operation_kind="personality_test",
        subject_kind="experiment",
        subject_id="evr_001",
        claims=(ResourceClaim("model_version", "mdl_001", "read"),),
    )

    blockers = coordinator.deletion_blockers(
        (ResourceClaim("model_version", "mdl_001", "write"),)
    )

    assert len(blockers) == 1
    assert blockers[0].operation.operation_kind == "personality_test"
    lease.succeed()
    assert coordinator.deletion_blockers(
        (ResourceClaim("model_version", "mdl_001", "write"),)
    ) == ()


def test_operation_can_attach_created_artifact_before_completion() -> None:
    _connection, coordinator = _coordinator()
    lease = coordinator.begin(
        operation_kind="training",
        subject_kind="training_run",
        subject_id="trn_001",
        claims=(ResourceClaim("training_run", "trn_001", "write"),),
    )

    lease.attach(ResourceClaim("artifact_path", "/artifacts/trn_001", "write"))

    assert ResourceClaim(
        "artifact_path", "/artifacts/trn_001", "write"
    ) in coordinator.claims_for(lease.operation_id)
    assert lease.succeed() is True
    assert lease.succeed() is False


def test_orphan_recovery_releases_resources() -> None:
    connection, coordinator = _coordinator()
    lease = coordinator.begin(
        operation_kind="training",
        subject_kind="training_run",
        subject_id="trn_orphan",
        claims=(ResourceClaim("model_version", "mdl_orphan", "read"),),
    )
    connection.execute(
        "UPDATE runtime_operations SET owner_pid = 99999999 WHERE id = ?",
        (lease.operation_id,),
    )
    connection.commit()
    coordinator._pid_is_alive = lambda _pid: False  # type: ignore[method-assign]

    assert coordinator.recover_orphaned_operations() == 1
    assert coordinator.active_operations() == ()
    assert coordinator.deletion_blockers(
        (ResourceClaim("model_version", "mdl_orphan", "write"),)
    ) == ()

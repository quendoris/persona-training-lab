from __future__ import annotations

import sqlite3

import pytest

from persona_training_lab.application.runtime.atomic import (
    RuntimeOperationCoordinator,
)
from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
)
from persona_training_lab.infrastructure.persistence.repositories.runtime_operations_atomic import (
    SQLiteRuntimeOperationsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


def _connect(path):
    connection = sqlite3.connect(path, timeout=2.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 2000")
    return connection


def test_atomic_leases_are_visible_across_database_connections(tmp_path) -> None:
    path = tmp_path / "runtime.sqlite3"
    first_connection = _connect(path)
    create_minimal_schema(first_connection)
    second_connection = _connect(path)
    first = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(first_connection)
    )
    second = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(second_connection)
    )
    lease = first.begin(
        operation_kind="training",
        subject_kind="training_run",
        subject_id="trn_001",
        claims=(ResourceClaim("artifact_path", "/models/one", "write"),),
    )

    with pytest.raises(OperationConflictError) as captured:
        second.begin(
            operation_kind="personality_test",
            subject_kind="experiment",
            subject_id="evr_001",
            claims=(ResourceClaim("artifact_path", "/models/one", "read"),),
        )

    assert captured.value.blockers[0].operation.operation_id == lease.operation_id
    lease.succeed()
    second_lease = second.begin(
        operation_kind="personality_test",
        subject_kind="experiment",
        subject_id="evr_001",
        claims=(ResourceClaim("artifact_path", "/models/one", "read"),),
    )
    second_lease.succeed()


def test_atomic_repository_allows_cross_connection_readers(tmp_path) -> None:
    path = tmp_path / "runtime.sqlite3"
    first_connection = _connect(path)
    create_minimal_schema(first_connection)
    second_connection = _connect(path)
    first = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(first_connection)
    )
    second = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(second_connection)
    )

    first_lease = first.begin(
        operation_kind="portrait",
        subject_kind="experiment",
        subject_id="evr_001",
        claims=(ResourceClaim("model_version", "mdl_001", "read"),),
    )
    second_lease = second.begin(
        operation_kind="analysis",
        subject_kind="analysis",
        subject_id="anl_001",
        claims=(ResourceClaim("model_version", "mdl_001", "read"),),
    )

    assert first_lease.closed is False
    assert second_lease.closed is False
    first_lease.succeed()
    second_lease.succeed()

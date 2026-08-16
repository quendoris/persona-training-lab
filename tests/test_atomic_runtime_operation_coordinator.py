from __future__ import annotations

import sqlite3
from threading import Barrier, Event, Lock, Thread

import pytest

from persona_training_lab.application.runtime.atomic import (
    RuntimeOperationCoordinator,
)
from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
)
from persona_training_lab.infrastructure.persistence.repositories.agents import (
    SQLiteAgentsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.analysis import (
    SQLiteAnalysisRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.datasets import (
    SQLiteDatasetsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.profiles import (
    SQLiteProfilesRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.projects import (
    SQLiteProjectsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.runtime_operations_atomic import (
    SQLiteRuntimeOperationsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.ui_preferences import (
    SQLiteUIPreferencesRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.locking import (
    connection_lock,
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


def test_shared_writable_connection_repositories_use_one_serialization_lock() -> None:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    expected_lock = connection_lock(connection)

    repositories = (
        SQLiteAgentsRepository(connection),
        SQLiteAnalysisRepository(connection),
        SQLiteDatasetsRepository(connection),
        SQLiteProfilesRepository(connection),
        SQLiteProjectsRepository(connection),
        SQLiteRuntimeOperationsRepository(connection),
        SQLiteUIPreferencesRepository(connection),
    )

    assert all(repository._lock is expected_lock for repository in repositories)
    connection.close()


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


def test_atomic_write_race_has_exactly_one_winner_across_connections(
    tmp_path,
) -> None:
    path = tmp_path / "runtime.sqlite3"
    bootstrap = _connect(path)
    create_minimal_schema(bootstrap)
    bootstrap.close()

    start = Barrier(2)
    release_winner = Event()
    both_attempted = Event()
    result_lock = Lock()
    outcomes: list[tuple[str, str, str]] = []
    errors: list[BaseException] = []

    def mark_attempted() -> None:
        if len(outcomes) + len(errors) == 2:
            both_attempted.set()

    def worker(subject_id: str) -> None:
        connection = sqlite3.connect(path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        coordinator = RuntimeOperationCoordinator(
            SQLiteRuntimeOperationsRepository(connection)
        )
        try:
            start.wait(timeout=5.0)
            try:
                lease = coordinator.begin(
                    operation_kind="training",
                    subject_kind="training_run",
                    subject_id=subject_id,
                    claims=(
                        ResourceClaim(
                            "artifact_path",
                            "/models/race-target",
                            "write",
                        ),
                    ),
                )
            except OperationConflictError as conflict:
                blocker_id = conflict.blockers[0].operation.operation_id
                with result_lock:
                    outcomes.append(("blocked", subject_id, blocker_id))
                    mark_attempted()
                return

            with result_lock:
                outcomes.append(("won", subject_id, lease.operation_id))
                mark_attempted()
            if not release_winner.wait(timeout=5.0):
                raise TimeoutError("winner release timed out")
            assert lease.succeed() is True
        except BaseException as error:
            with result_lock:
                errors.append(error)
                mark_attempted()
        finally:
            connection.close()

    threads = (
        Thread(target=worker, args=("trn_race_a",), daemon=True),
        Thread(target=worker, args=("trn_race_b",), daemon=True),
    )
    for thread in threads:
        thread.start()

    observer = None
    try:
        assert both_attempted.wait(timeout=7.0), "race participants timed out"
        assert errors == []
        assert sorted(outcome[0] for outcome in outcomes) == ["blocked", "won"]

        winner = next(outcome for outcome in outcomes if outcome[0] == "won")
        blocked = next(outcome for outcome in outcomes if outcome[0] == "blocked")
        assert blocked[2] == winner[2]

        observer = _connect(path)
        active = RuntimeOperationCoordinator(
            SQLiteRuntimeOperationsRepository(observer)
        ).active_operations()
        assert len(active) == 1
        assert active[0].operation_id == winner[2]
    finally:
        release_winner.set()
        for thread in threads:
            thread.join(timeout=7.0)
        if observer is not None:
            observer.close()

    assert all(not thread.is_alive() for thread in threads)
    assert errors == []

    final_connection = _connect(path)
    try:
        final = RuntimeOperationCoordinator(
            SQLiteRuntimeOperationsRepository(final_connection)
        )
        assert final.active_operations() == ()
        retry = final.begin(
            operation_kind="training",
            subject_kind="training_run",
            subject_id="trn_after_race",
            claims=(
                ResourceClaim(
                    "artifact_path",
                    "/models/race-target",
                    "write",
                ),
            ),
        )
        assert retry.succeed() is True
    finally:
        final_connection.close()

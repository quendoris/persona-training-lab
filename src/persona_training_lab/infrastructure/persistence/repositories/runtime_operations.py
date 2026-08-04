from __future__ import annotations

import sqlite3

from persona_training_lab.application.runtime.operations import (
    ACTIVE_OPERATION_STATES,
    ResourceClaim,
    RuntimeOperation,
)
from persona_training_lab.infrastructure.persistence.sqlite.locking import (
    connection_lock,
)


class SQLiteRuntimeOperationsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = connection_lock(connection)

    def create_operation(
        self,
        operation: RuntimeOperation,
        claims: tuple[ResourceClaim, ...],
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO runtime_operations (
                    id, operation_kind, subject_kind, subject_id, state,
                    correlation_id, owner_pid, started_at, heartbeat_at,
                    finished_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operation.operation_id,
                    operation.operation_kind,
                    operation.subject_kind,
                    operation.subject_id,
                    operation.state,
                    operation.correlation_id,
                    operation.owner_pid,
                    operation.started_at,
                    operation.heartbeat_at,
                    operation.finished_at,
                    operation.error_message,
                ),
            )
            self._insert_claims(operation.operation_id, claims)

    def get_operation(
        self,
        operation_id: str,
    ) -> RuntimeOperation | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, operation_kind, subject_kind, subject_id, state,
                       correlation_id, owner_pid, started_at, heartbeat_at,
                       finished_at, error_message
                FROM runtime_operations
                WHERE id = ?
                """,
                (operation_id,),
            ).fetchone()
        return self._to_operation(row)

    def list_active_operations(self) -> list[RuntimeOperation]:
        placeholders = ",".join("?" for _ in ACTIVE_OPERATION_STATES)
        with self._lock:
            rows = self._connection.execute(
                f"""
                SELECT id, operation_kind, subject_kind, subject_id, state,
                       correlation_id, owner_pid, started_at, heartbeat_at,
                       finished_at, error_message
                FROM runtime_operations
                WHERE state IN ({placeholders})
                ORDER BY started_at ASC, id ASC
                """,
                tuple(sorted(ACTIVE_OPERATION_STATES)),
            ).fetchall()
        return [
            operation
            for row in rows
            if (operation := self._to_operation(row)) is not None
        ]

    def list_claims(
        self,
        operation_id: str,
    ) -> tuple[ResourceClaim, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT resource_kind, resource_id, access_mode
                FROM runtime_operation_resources
                WHERE operation_id = ?
                ORDER BY resource_kind, resource_id
                """,
                (operation_id,),
            ).fetchall()
        return tuple(
            ResourceClaim(
                resource_kind=str(row["resource_kind"]),
                resource_id=str(row["resource_id"]),
                access_mode=str(row["access_mode"]),
            )
            for row in rows
        )

    def add_claims(
        self,
        operation_id: str,
        claims: tuple[ResourceClaim, ...],
    ) -> None:
        if not claims:
            return
        with self._lock, self._connection:
            self._insert_claims(operation_id, claims)

    def heartbeat(
        self,
        operation_id: str,
        heartbeat_at: str,
    ) -> bool:
        placeholders = ",".join("?" for _ in ACTIVE_OPERATION_STATES)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                f"""
                UPDATE runtime_operations
                SET heartbeat_at = ?
                WHERE id = ? AND state IN ({placeholders})
                """,
                (
                    heartbeat_at,
                    operation_id,
                    *tuple(sorted(ACTIVE_OPERATION_STATES)),
                ),
            )
        return cursor.rowcount > 0

    def finish_operation(
        self,
        operation_id: str,
        *,
        state: str,
        finished_at: str,
        error_message: str,
    ) -> bool:
        placeholders = ",".join("?" for _ in ACTIVE_OPERATION_STATES)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                f"""
                UPDATE runtime_operations
                SET state = ?, heartbeat_at = ?, finished_at = ?,
                    error_message = ?
                WHERE id = ? AND state IN ({placeholders})
                """,
                (
                    state,
                    finished_at,
                    finished_at,
                    error_message,
                    operation_id,
                    *tuple(sorted(ACTIVE_OPERATION_STATES)),
                ),
            )
        return cursor.rowcount > 0

    def abandon_operations(
        self,
        operation_ids: tuple[str, ...],
        at: str,
    ) -> int:
        if not operation_ids:
            return 0
        operation_placeholders = ",".join("?" for _ in operation_ids)
        state_placeholders = ",".join("?" for _ in ACTIVE_OPERATION_STATES)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                f"""
                UPDATE runtime_operations
                SET state = 'abandoned', heartbeat_at = ?, finished_at = ?,
                    error_message = CASE
                        WHEN error_message = ''
                        THEN 'Операция прервана завершением процесса'
                        ELSE error_message
                    END
                WHERE id IN ({operation_placeholders})
                  AND state IN ({state_placeholders})
                """,
                (
                    at,
                    at,
                    *operation_ids,
                    *tuple(sorted(ACTIVE_OPERATION_STATES)),
                ),
            )
        return cursor.rowcount

    def _insert_claims(
        self,
        operation_id: str,
        claims: tuple[ResourceClaim, ...],
    ) -> None:
        self._connection.executemany(
            """
            INSERT INTO runtime_operation_resources (
                operation_id, resource_kind, resource_id, access_mode
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(operation_id, resource_kind, resource_id)
            DO UPDATE SET access_mode = CASE
                WHEN excluded.access_mode = 'write' THEN 'write'
                ELSE runtime_operation_resources.access_mode
            END
            """,
            (
                (
                    operation_id,
                    claim.resource_kind,
                    claim.resource_id,
                    claim.access_mode,
                )
                for claim in claims
            ),
        )

    @staticmethod
    def _to_operation(row) -> RuntimeOperation | None:
        if row is None:
            return None
        return RuntimeOperation(
            operation_id=str(row["id"]),
            operation_kind=str(row["operation_kind"]),
            subject_kind=str(row["subject_kind"]),
            subject_id=str(row["subject_id"]),
            state=str(row["state"]),
            correlation_id=str(row["correlation_id"]),
            owner_pid=int(row["owner_pid"]),
            started_at=str(row["started_at"]),
            heartbeat_at=str(row["heartbeat_at"]),
            finished_at=str(row["finished_at"]),
            error_message=str(row["error_message"]),
        )

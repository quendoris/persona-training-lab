from __future__ import annotations

from persona_training_lab.application.runtime.operations import (
    ACTIVE_OPERATION_STATES,
    OperationBlocker,
    ResourceClaim,
    RuntimeOperation,
)
from persona_training_lab.infrastructure.persistence.repositories.runtime_operations import (
    SQLiteRuntimeOperationsRepository as _SQLiteRuntimeOperationsRepository,
)


class SQLiteRuntimeOperationsRepository(_SQLiteRuntimeOperationsRepository):
    """SQLite repository acquiring resource leases inside BEGIN IMMEDIATE."""

    def try_create_operation(
        self,
        operation: RuntimeOperation,
        claims: tuple[ResourceClaim, ...],
    ) -> tuple[OperationBlocker, ...]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                blockers = self._conflict_blockers(claims)
                if blockers:
                    self._connection.rollback()
                    return blockers
                self._insert_operation(operation)
                self._insert_claims(operation.operation_id, claims)
                self._connection.commit()
                return ()
            except Exception:
                self._connection.rollback()
                raise

    def try_add_claims(
        self,
        operation_id: str,
        claims: tuple[ResourceClaim, ...],
    ) -> tuple[OperationBlocker, ...]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                blockers = self._conflict_blockers(
                    claims,
                    exclude_operation_id=operation_id,
                )
                if blockers:
                    self._connection.rollback()
                    return blockers
                operation = self.get_operation(operation_id)
                if operation is None or operation.state not in ACTIVE_OPERATION_STATES:
                    self._connection.rollback()
                    raise RuntimeError(
                        "Cannot attach resources to an inactive operation"
                    )
                self._insert_claims(operation_id, claims)
                self._connection.commit()
                return ()
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def _insert_operation(self, operation: RuntimeOperation) -> None:
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

    def _conflict_blockers(
        self,
        requested: tuple[ResourceClaim, ...],
        *,
        exclude_operation_id: str = "",
    ) -> tuple[OperationBlocker, ...]:
        requested_by_key = {claim.key: claim for claim in requested}
        if not requested_by_key:
            return ()
        placeholders = ",".join("?" for _ in ACTIVE_OPERATION_STATES)
        rows = self._connection.execute(
            f"""
            SELECT o.id, o.operation_kind, o.subject_kind, o.subject_id,
                   o.state, o.correlation_id, o.owner_pid, o.started_at,
                   o.heartbeat_at, o.finished_at, o.error_message,
                   r.resource_kind, r.resource_id, r.access_mode
            FROM runtime_operations AS o
            JOIN runtime_operation_resources AS r
              ON r.operation_id = o.id
            WHERE o.state IN ({placeholders})
              AND o.id != ?
            ORDER BY o.started_at, o.id, r.resource_kind, r.resource_id
            """,
            (*tuple(sorted(ACTIVE_OPERATION_STATES)), exclude_operation_id),
        ).fetchall()

        blockers: list[OperationBlocker] = []
        for row in rows:
            active_claim = ResourceClaim(
                str(row["resource_kind"]),
                str(row["resource_id"]),
                str(row["access_mode"]),
            )
            candidate = requested_by_key.get(active_claim.key)
            if candidate is None:
                continue
            if (
                candidate.access_mode != "write"
                and active_claim.access_mode != "write"
            ):
                continue
            operation = RuntimeOperation(
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
            blockers.append(OperationBlocker(operation, active_claim))
        return tuple(blockers)

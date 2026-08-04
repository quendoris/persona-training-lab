from __future__ import annotations

from os import getpid
from uuid import uuid4

from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
    RuntimeOperation,
    RuntimeOperationCoordinator as _RuntimeOperationCoordinator,
    RuntimeOperationLease,
    _utc_now,
)


class RuntimeOperationCoordinator(_RuntimeOperationCoordinator):
    """Coordinator using repository-level atomic lock acquisition when available."""

    def begin(
        self,
        *,
        operation_kind: str,
        subject_kind: str,
        subject_id: str,
        claims,
        correlation_id: str | None = None,
    ) -> RuntimeOperationLease:
        atomic_creator = getattr(
            self._repository,
            "try_create_operation",
            None,
        )
        if not callable(atomic_creator):
            return super().begin(
                operation_kind=operation_kind,
                subject_kind=subject_kind,
                subject_id=subject_id,
                claims=claims,
                correlation_id=correlation_id,
            )

        normalized_claims = self._normalise_claims(claims)
        if not normalized_claims:
            normalized_claims = (
                ResourceClaim(subject_kind, subject_id, "write"),
            )
        now = _utc_now()
        operation = RuntimeOperation(
            operation_id=f"op_{uuid4().hex[:12]}",
            operation_kind=operation_kind.strip().casefold() or "operation",
            subject_kind=subject_kind.strip().casefold() or "entity",
            subject_id=subject_id.strip(),
            state="running",
            correlation_id=(
                correlation_id or f"corr_{uuid4().hex[:12]}"
            ),
            owner_pid=getpid(),
            started_at=now,
            heartbeat_at=now,
        )
        with self._lock:
            blockers = tuple(
                atomic_creator(operation, normalized_claims)
            )
        if blockers:
            raise OperationConflictError(blockers)
        return RuntimeOperationLease(self, operation, normalized_claims)

    def attach_claims(
        self,
        operation_id: str,
        claims,
    ) -> tuple[ResourceClaim, ...]:
        normalized = self._normalise_claims(claims)
        if not normalized:
            return ()
        atomic_attacher = getattr(
            self._repository,
            "try_add_claims",
            None,
        )
        if not callable(atomic_attacher):
            return super().attach_claims(operation_id, normalized)
        with self._lock:
            blockers = tuple(
                atomic_attacher(operation_id, normalized)
            )
        if blockers:
            raise OperationConflictError(blockers)
        return normalized

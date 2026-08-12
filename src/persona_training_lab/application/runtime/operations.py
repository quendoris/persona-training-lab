from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from os import getpid, kill
from threading import RLock
from typing import Iterable, Literal, Protocol
from uuid import uuid4


ACTIVE_OPERATION_STATES = frozenset({"starting", "running", "cancelling"})
TERMINAL_OPERATION_STATES = frozenset(
    {"succeeded", "failed", "cancelled", "abandoned"}
)
VALID_ACCESS_MODES = frozenset({"read", "write"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True, frozen=True, order=True)
class ResourceClaim:
    resource_kind: str
    resource_id: str
    access_mode: str = "read"

    def __post_init__(self) -> None:
        kind = self.resource_kind.strip().casefold()
        identifier = self.resource_id.strip()
        mode = self.access_mode.strip().casefold()
        if not kind:
            raise ValueError("resource_kind must not be empty")
        if not identifier:
            raise ValueError("resource_id must not be empty")
        if mode not in VALID_ACCESS_MODES:
            raise ValueError(f"Unsupported resource access mode: {mode}")
        object.__setattr__(self, "resource_kind", kind)
        object.__setattr__(self, "resource_id", identifier)
        object.__setattr__(self, "access_mode", mode)

    @property
    def key(self) -> tuple[str, str]:
        return self.resource_kind, self.resource_id


@dataclass(slots=True, frozen=True)
class RuntimeOperation:
    operation_id: str
    operation_kind: str
    subject_kind: str
    subject_id: str
    state: str
    correlation_id: str
    owner_pid: int
    started_at: str
    heartbeat_at: str
    finished_at: str = ""
    error_message: str = ""


@dataclass(slots=True, frozen=True)
class OperationBlocker:
    operation: RuntimeOperation
    claim: ResourceClaim

    @property
    def message(self) -> str:
        return (
            f"{self.operation.operation_kind}: "
            f"{self.claim.resource_kind}={self.claim.resource_id}"
        )


class OperationConflictError(RuntimeError):
    def __init__(self, blockers: Iterable[OperationBlocker]) -> None:
        self.blockers = tuple(blockers)
        summary = ", ".join(item.message for item in self.blockers)
        super().__init__(
            "Ресурс уже используется активной операцией"
            + (f": {summary}" if summary else "")
        )


class RuntimeOperationRepositoryPort(Protocol):
    def create_operation(
        self,
        operation: RuntimeOperation,
        claims: tuple[ResourceClaim, ...],
    ) -> None: ...

    def get_operation(self, operation_id: str) -> RuntimeOperation | None: ...

    def list_active_operations(self) -> list[RuntimeOperation]: ...

    def list_claims(self, operation_id: str) -> tuple[ResourceClaim, ...]: ...

    def add_claims(
        self,
        operation_id: str,
        claims: tuple[ResourceClaim, ...],
    ) -> None: ...

    def heartbeat(self, operation_id: str, heartbeat_at: str) -> bool: ...

    def finish_operation(
        self,
        operation_id: str,
        *,
        state: str,
        finished_at: str,
        error_message: str,
    ) -> bool: ...

    def abandon_operations(self, operation_ids: tuple[str, ...], at: str) -> int: ...


class RuntimeOperationCoordinator:
    """Persistent resource leases for training, testing and inference jobs.

    Operations claim resources in read or write mode. Concurrent reads are
    allowed; any write conflicts with every other claim for the same resource.
    Destructive actions use :meth:`deletion_blockers`, where every active claim
    blocks deletion regardless of its access mode.
    """

    def __init__(self, repository: RuntimeOperationRepositoryPort) -> None:
        self._repository = repository
        self._lock = RLock()

    def begin(
        self,
        *,
        operation_kind: str,
        subject_kind: str,
        subject_id: str,
        claims: Iterable[ResourceClaim],
        correlation_id: str | None = None,
    ) -> RuntimeOperationLease:
        normalized_claims = self._normalise_claims(claims)
        if not normalized_claims:
            normalized_claims = (
                ResourceClaim(subject_kind, subject_id, "write"),
            )

        with self._lock:
            blockers = self.conflict_blockers(normalized_claims)
            if blockers:
                raise OperationConflictError(blockers)

            now = _utc_now()
            operation = RuntimeOperation(
                operation_id=f"op_{uuid4().hex[:12]}",
                operation_kind=operation_kind.strip().casefold() or "operation",
                subject_kind=subject_kind.strip().casefold() or "entity",
                subject_id=subject_id.strip(),
                state="running",
                correlation_id=(correlation_id or f"corr_{uuid4().hex[:12]}"),
                owner_pid=getpid(),
                started_at=now,
                heartbeat_at=now,
            )
            self._repository.create_operation(operation, normalized_claims)
            return RuntimeOperationLease(self, operation, normalized_claims)

    def active_operations(self) -> tuple[RuntimeOperation, ...]:
        return tuple(self._repository.list_active_operations())

    def claims_for(self, operation_id: str) -> tuple[ResourceClaim, ...]:
        return self._repository.list_claims(operation_id)

    def conflict_blockers(
        self,
        claims: Iterable[ResourceClaim],
        *,
        exclude_operation_id: str = "",
    ) -> tuple[OperationBlocker, ...]:
        requested = self._normalise_claims(claims)
        requested_by_key: dict[tuple[str, str], tuple[ResourceClaim, ...]] = {}
        for claim in requested:
            requested_by_key.setdefault(claim.key, ())
            requested_by_key[claim.key] = (*requested_by_key[claim.key], claim)

        blockers: list[OperationBlocker] = []
        for operation in self._repository.list_active_operations():
            if operation.operation_id == exclude_operation_id:
                continue
            for active_claim in self._repository.list_claims(
                operation.operation_id
            ):
                candidates = requested_by_key.get(active_claim.key, ())
                if not candidates:
                    continue
                if any(
                    candidate.access_mode == "write"
                    or active_claim.access_mode == "write"
                    for candidate in candidates
                ):
                    blockers.append(OperationBlocker(operation, active_claim))
        return tuple(blockers)

    def deletion_blockers(
        self,
        claims: Iterable[ResourceClaim],
    ) -> tuple[OperationBlocker, ...]:
        protected_keys = {claim.key for claim in self._normalise_claims(claims)}
        if not protected_keys:
            return ()
        blockers: list[OperationBlocker] = []
        for operation in self._repository.list_active_operations():
            for active_claim in self._repository.list_claims(
                operation.operation_id
            ):
                if active_claim.key in protected_keys:
                    blockers.append(OperationBlocker(operation, active_claim))
        return tuple(blockers)

    def attach_claims(
        self,
        operation_id: str,
        claims: Iterable[ResourceClaim],
    ) -> tuple[ResourceClaim, ...]:
        normalized = self._normalise_claims(claims)
        if not normalized:
            return ()
        with self._lock:
            blockers = self.conflict_blockers(
                normalized,
                exclude_operation_id=operation_id,
            )
            if blockers:
                raise OperationConflictError(blockers)
            self._repository.add_claims(operation_id, normalized)
        return normalized

    def heartbeat(self, operation_id: str) -> bool:
        return self._repository.heartbeat(operation_id, _utc_now())

    def finish(
        self,
        operation_id: str,
        *,
        state: str,
        error_message: str = "",
    ) -> bool:
        normalized_state = state.strip().casefold()
        if normalized_state not in TERMINAL_OPERATION_STATES:
            raise ValueError(f"Unsupported terminal state: {state}")
        return self._repository.finish_operation(
            operation_id,
            state=normalized_state,
            finished_at=_utc_now(),
            error_message=error_message.strip(),
        )

    def recover_orphaned_operations(self) -> int:
        orphaned = tuple(
            operation.operation_id
            for operation in self._repository.list_active_operations()
            if operation.owner_pid > 0 and not self._pid_is_alive(operation.owner_pid)
        )
        if not orphaned:
            return 0
        return self._repository.abandon_operations(orphaned, _utc_now())

    @staticmethod
    def _pid_is_alive(pid: int) -> bool:
        if pid == getpid():
            return True
        try:
            kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    @staticmethod
    def _normalise_claims(
        claims: Iterable[ResourceClaim],
    ) -> tuple[ResourceClaim, ...]:
        unique: dict[tuple[str, str], ResourceClaim] = {}
        for claim in claims:
            existing = unique.get(claim.key)
            if existing is None or claim.access_mode == "write":
                unique[claim.key] = claim
        return tuple(sorted(unique.values()))


class RuntimeOperationLease:
    def __init__(
        self,
        coordinator: RuntimeOperationCoordinator,
        operation: RuntimeOperation,
        claims: tuple[ResourceClaim, ...],
    ) -> None:
        self._coordinator = coordinator
        self.operation = operation
        self._claims = list(claims)
        self._closed = False
        self._lock = RLock()

    @property
    def operation_id(self) -> str:
        return self.operation.operation_id

    @property
    def correlation_id(self) -> str:
        return self.operation.correlation_id

    @property
    def claims(self) -> tuple[ResourceClaim, ...]:
        return tuple(self._claims)

    @property
    def closed(self) -> bool:
        return self._closed

    def attach(self, *claims: ResourceClaim) -> None:
        with self._lock:
            if self._closed:
                return
            attached = self._coordinator.attach_claims(
                self.operation_id,
                claims,
            )
            self._claims.extend(
                claim for claim in attached if claim not in self._claims
            )

    def heartbeat(self) -> bool:
        if self._closed:
            return False
        return self._coordinator.heartbeat(self.operation_id)

    def succeed(self) -> bool:
        return self._close("succeeded")

    def fail(self, message: str) -> bool:
        return self._close("failed", message)

    def cancel(self, message: str = "") -> bool:
        return self._close("cancelled", message)

    def _close(self, state: str, message: str = "") -> bool:
        with self._lock:
            if self._closed:
                return False
            changed = self._coordinator.finish(
                self.operation_id,
                state=state,
                error_message=message,
            )
            self._closed = True
            return changed

    def __enter__(self) -> RuntimeOperationLease:
        return self

    def __exit__(self, exc_type, exc, _traceback) -> Literal[False]:
        if exc is None:
            self.succeed()
        else:
            self.fail(str(exc))
        return False

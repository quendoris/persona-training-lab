from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from persona_training_lab.application.runtime.operations import (
    OperationBlocker,
    OperationConflictError,
)
from persona_training_lab.ui.agents.runtime_policy import (
    LineageBranchTransactions,
)


class BranchDeletionStatus(StrEnum):
    DELETED = "deleted"
    BLOCKED = "blocked"
    STALE = "stale"
    NOOP = "noop"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class BranchDeletionPlan:
    node_id: str
    node_title: str
    removed_ids: tuple[str, ...]
    fallback_id: str

    @property
    def descendant_count(self) -> int:
        return max(0, len(self.removed_ids) - 1)


@dataclass(frozen=True, slots=True)
class BranchDeletionResult:
    status: BranchDeletionStatus
    removed_ids: tuple[str, ...] = ()
    fallback_id: str = ""
    blockers: tuple[OperationBlocker, ...] = ()


class BranchDeletionStatePort(Protocol):
    def custom_subtree_ids(self, node_id: str) -> tuple[str, ...]: ...

    def delete_subtree(
        self,
        node_id: str,
        layout_snapshot: dict[str, Any] | None = None,
    ) -> tuple[str, ...]: ...

    def capture_transaction_state(self) -> dict[str, Any]: ...

    def restore_transaction_state(self, snapshot: dict[str, Any]) -> None: ...


class BranchDeletionExecutionError(RuntimeError):
    def __init__(
        self,
        original_error: BaseException,
        compensation_errors: tuple[BaseException, ...],
    ) -> None:
        self.original_error = original_error
        self.compensation_errors = compensation_errors
        details = "; ".join(
            f"{type(error).__name__}: {error}"
            for error in compensation_errors
        )
        super().__init__(
            f"Branch deletion failed: {original_error}. "
            f"Compensation also failed: {details}"
        )


class BranchDeletionCommittedError(RuntimeError):
    def __init__(
        self,
        result: BranchDeletionResult,
        finalization_error: BaseException,
    ) -> None:
        self.result = result
        self.finalization_error = finalization_error
        super().__init__(
            "Branch deletion committed, but runtime lease finalization failed: "
            f"{finalization_error}"
        )


class BranchDeletionController:
    """Coordinate durable state deletion and safety-link cleanup."""

    def __init__(
        self,
        state: BranchDeletionStatePort,
        transactions: LineageBranchTransactions,
    ) -> None:
        self._state = state
        self._transactions = transactions

    def prepare(
        self,
        node_id: str,
        *,
        node_title: str,
        parent_id: str,
        graph_current_id: str,
    ) -> BranchDeletionPlan | None:
        removed_ids = self._state.custom_subtree_ids(node_id)
        if not removed_ids:
            return None
        return BranchDeletionPlan(
            node_id=node_id,
            node_title=node_title,
            removed_ids=removed_ids,
            fallback_id=parent_id or graph_current_id,
        )

    def execute(
        self,
        plan: BranchDeletionPlan,
        *,
        layout_snapshot: dict[str, Any] | None = None,
    ) -> BranchDeletionResult:
        current_ids = self._state.custom_subtree_ids(plan.node_id)
        if not current_ids:
            return BranchDeletionResult(BranchDeletionStatus.NOOP)
        if current_ids != plan.removed_ids:
            return BranchDeletionResult(
                BranchDeletionStatus.STALE,
                removed_ids=current_ids,
                fallback_id=plan.fallback_id,
            )

        try:
            lease = self._transactions.begin_deletion(
                plan.removed_ids,
                subject_id=plan.node_id,
            )
        except OperationConflictError as conflict:
            return BranchDeletionResult(
                BranchDeletionStatus.BLOCKED,
                blockers=conflict.blockers,
            )
        if lease is None:
            return BranchDeletionResult(BranchDeletionStatus.UNAVAILABLE)

        transaction_snapshot = self._state.capture_transaction_state()
        try:
            removed_ids = self._state.delete_subtree(
                plan.node_id,
                layout_snapshot,
            )
        except Exception as error:
            self._fail_lease_or_raise(lease, error)
            raise

        if removed_ids != plan.removed_ids:
            compensation_errors = self._restore_and_close(
                transaction_snapshot,
                lease,
                cancel=True,
                message="Lineage subtree changed during deletion",
            )
            if compensation_errors:
                raise BranchDeletionExecutionError(
                    RuntimeError("Lineage subtree changed during deletion"),
                    compensation_errors,
                )
            return BranchDeletionResult(
                BranchDeletionStatus.STALE,
                removed_ids=removed_ids,
                fallback_id=plan.fallback_id,
            )

        try:
            self._transactions.forget(removed_ids)
        except Exception as error:
            compensation_errors = self._restore_and_close(
                transaction_snapshot,
                lease,
                cancel=False,
                message=str(error),
            )
            if compensation_errors:
                raise BranchDeletionExecutionError(
                    error,
                    compensation_errors,
                ) from error
            raise

        result = BranchDeletionResult(
            BranchDeletionStatus.DELETED,
            removed_ids=removed_ids,
            fallback_id=plan.fallback_id,
        )
        try:
            lease.succeed()
        except Exception as error:
            raise BranchDeletionCommittedError(result, error) from error
        return result

    def _restore_and_close(
        self,
        snapshot: dict[str, Any],
        lease,
        *,
        cancel: bool,
        message: str,
    ) -> tuple[BaseException, ...]:
        errors: list[BaseException] = []
        try:
            self._state.restore_transaction_state(snapshot)
        except Exception as error:
            errors.append(error)
        try:
            if cancel:
                lease.cancel(message)
            else:
                lease.fail(message)
        except Exception as error:
            errors.append(error)
        return tuple(errors)

    @staticmethod
    def _fail_lease_or_raise(lease, original_error: BaseException) -> None:
        try:
            lease.fail(str(original_error))
        except Exception as finalization_error:
            raise BranchDeletionExecutionError(
                original_error,
                (finalization_error,),
            ) from original_error


__all__ = (
    "BranchDeletionCommittedError",
    "BranchDeletionController",
    "BranchDeletionExecutionError",
    "BranchDeletionPlan",
    "BranchDeletionResult",
    "BranchDeletionStatus",
)

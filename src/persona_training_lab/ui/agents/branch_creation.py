from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.runtime_policy import (
    LineageBranchTransactions,
)


class BranchCreationStatePort(Protocol):
    def continue_from(
        self,
        parent_id: str,
        layout_snapshot: dict[str, Any] | None = None,
    ) -> str: ...

    def capture_transaction_state(self) -> dict[str, Any]: ...

    def restore_transaction_state(self, snapshot: dict[str, Any]) -> None: ...


class BranchCreationExecutionError(RuntimeError):
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
            f"Branch creation failed: {original_error}. "
            f"Compensation also failed: {details}"
        )


@dataclass(slots=True)
class BranchCreationController:
    """Create one durable local branch and its safety links as one workflow."""

    state: BranchCreationStatePort
    transactions: LineageBranchTransactions

    def execute(
        self,
        parent_id: str,
        *,
        parent_is_custom: bool,
        fallback_claims: Iterable[ResourceClaim],
        layout_snapshot: dict[str, Any] | None = None,
    ) -> str:
        transaction_snapshot = self.state.capture_transaction_state()
        child_id = self.state.continue_from(parent_id, layout_snapshot)
        try:
            self.transactions.bind_child(
                child_id,
                parent_id,
                parent_is_custom=parent_is_custom,
                fallback_claims=fallback_claims,
            )
        except Exception as error:
            try:
                self.state.restore_transaction_state(transaction_snapshot)
            except Exception as compensation_error:
                raise BranchCreationExecutionError(
                    error,
                    (compensation_error,),
                ) from error
            raise
        return child_id


__all__ = (
    "BranchCreationController",
    "BranchCreationExecutionError",
    "BranchCreationStatePort",
)

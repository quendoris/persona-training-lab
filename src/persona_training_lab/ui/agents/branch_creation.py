from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from persona_training_lab.application.runtime.operations import (
    ResourceClaim,
    RuntimeOperationLease,
)
from persona_training_lab.ui.agents.lineage_state import HistoryTransition
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

    def attach_latest_history_metadata(
        self,
        action_code: str,
        metadata: dict[str, Any],
    ) -> None: ...

    def custom_subtree_ids(self, node_id: str) -> tuple[str, ...]: ...

    def undo_only(
        self,
        current_layout: dict[str, Any] | None = None,
    ) -> HistoryTransition | None: ...

    def redo_last_action(
        self,
        current_layout: dict[str, Any] | None = None,
    ) -> HistoryTransition | None: ...


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


class BranchCreationHistoryCommittedError(RuntimeError):
    def __init__(
        self,
        transition: HistoryTransition,
        finalization_error: BaseException,
    ) -> None:
        self.transition = transition
        self.finalization_error = finalization_error
        super().__init__(
            "Branch creation Undo committed, but runtime lease finalization "
            f"failed: {finalization_error}"
        )


@dataclass(slots=True)
class BranchCreationController:
    """Keep custom-branch state and its persisted safety links consistent."""

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
        links_bound = False
        try:
            bound_claims = self.transactions.bind_child(
                child_id,
                parent_id,
                parent_is_custom=parent_is_custom,
                fallback_claims=fallback_claims,
            )
            links_bound = True
            metadata = self.transactions.capture_creation_history(
                child_id,
                bound_claims,
            )
            if not metadata:
                raise RuntimeError(
                    "Branch creation history metadata could not be captured"
                )
            self.state.attach_latest_history_metadata(
                "branch_create",
                metadata,
            )
        except Exception as error:
            compensation_errors: list[BaseException] = []
            state_restored = False
            try:
                self.state.restore_transaction_state(transaction_snapshot)
                state_restored = True
            except Exception as compensation_error:
                compensation_errors.append(compensation_error)

            if links_bound and state_restored:
                try:
                    self.transactions.forget((child_id,))
                except Exception as compensation_error:
                    compensation_errors.append(compensation_error)

            if compensation_errors:
                raise BranchCreationExecutionError(
                    error,
                    tuple(compensation_errors),
                ) from error
            raise
        return child_id

    def supports_history(self, metadata: Mapping[str, Any]) -> bool:
        return bool(self.transactions.creation_history_child(metadata))

    def undo_history(
        self,
        metadata: Mapping[str, Any],
        *,
        current_layout: dict[str, Any] | None = None,
    ) -> HistoryTransition | None:
        child_id = self.transactions.creation_history_child(metadata)
        if not child_id:
            return None

        current_ids = self.state.custom_subtree_ids(child_id)
        if current_ids != (child_id,):
            raise RuntimeError(
                "Lineage branch creation Undo no longer matches current subtree"
            )
        if not self.transactions.creation_history_matches_current_links(metadata):
            raise RuntimeError(
                "Lineage branch creation Undo safety links no longer match "
                "recorded history"
            )

        transaction_snapshot = self.state.capture_transaction_state()
        lease = self.transactions.begin_deletion(
            current_ids,
            subject_id=child_id,
        )
        if not self.transactions.creation_history_matches_current_links(metadata):
            error = RuntimeError(
                "Lineage branch creation Undo safety links changed during "
                "runtime guard acquisition"
            )
            compensation_errors = self._close_lease(
                lease,
                cancel=True,
                message=str(error),
            )
            if compensation_errors:
                raise BranchCreationExecutionError(
                    error,
                    compensation_errors,
                ) from error
            raise error

        try:
            transition = self.state.undo_only(current_layout)
        except Exception as error:
            self._fail_lease_or_raise(lease, error)
            raise

        if (
            transition is None
            or transition.action_code != "branch_create"
            or transition.direction != "undo"
        ):
            error = RuntimeError(
                "Lineage branch creation Undo no longer matches history"
            )
            compensation_errors = self._restore_and_close(
                transaction_snapshot,
                lease,
                cancel=True,
                message=str(error),
            )
            if compensation_errors:
                raise BranchCreationExecutionError(
                    error,
                    compensation_errors,
                ) from error
            raise error

        try:
            forgotten_id = self.transactions.forget_creation_history(metadata)
        except Exception as error:
            compensation_errors = self._restore_and_close(
                transaction_snapshot,
                lease,
                cancel=False,
                message=str(error),
            )
            if compensation_errors:
                raise BranchCreationExecutionError(
                    error,
                    compensation_errors,
                ) from error
            raise

        if forgotten_id != child_id:
            error = RuntimeError(
                "Lineage branch creation Undo lost its safety identity"
            )
            compensation_errors = self._restore_and_close(
                transaction_snapshot,
                lease,
                cancel=False,
                message=str(error),
                restore_links=metadata,
            )
            if compensation_errors:
                raise BranchCreationExecutionError(
                    error,
                    compensation_errors,
                ) from error
            raise error

        self._finalize_committed_undo(lease, transition)
        return transition

    def redo_history(
        self,
        metadata: Mapping[str, Any],
        *,
        current_layout: dict[str, Any] | None = None,
    ) -> HistoryTransition | None:
        child_id = self.transactions.creation_history_child(metadata)
        if not child_id:
            return None
        if self.state.custom_subtree_ids(child_id):
            raise RuntimeError(
                "Lineage branch creation Redo target already exists"
            )

        transaction_snapshot = self.state.capture_transaction_state()
        try:
            transition = self.state.redo_last_action(current_layout)
            if (
                transition is None
                or transition.action_code != "branch_create"
                or transition.direction != "redo"
            ):
                raise RuntimeError(
                    "Lineage branch creation Redo no longer matches history"
                )
            if self.state.custom_subtree_ids(child_id) != (child_id,):
                raise RuntimeError(
                    "Lineage branch creation Redo restored unexpected subtree"
                )
            restored_id = self.transactions.restore_creation_history(metadata)
            if restored_id != child_id:
                raise RuntimeError(
                    "Lineage branch creation Redo lost its safety identity"
                )
            if not self.transactions.creation_history_matches_current_links(
                metadata
            ):
                raise RuntimeError(
                    "Lineage branch creation Redo did not restore recorded "
                    "safety links"
                )
            return transition
        except Exception as error:
            self._restore_state_or_raise(
                transaction_snapshot,
                error,
            )
            raise

    def _restore_state_or_raise(
        self,
        snapshot: dict[str, Any],
        original_error: BaseException,
    ) -> None:
        try:
            self.state.restore_transaction_state(snapshot)
        except Exception as compensation_error:
            raise BranchCreationExecutionError(
                original_error,
                (compensation_error,),
            ) from original_error

    def _restore_and_close(
        self,
        snapshot: dict[str, Any],
        lease: RuntimeOperationLease | None,
        *,
        cancel: bool,
        message: str,
        restore_links: Mapping[str, Any] | None = None,
    ) -> tuple[BaseException, ...]:
        errors: list[BaseException] = []
        state_restored = False
        try:
            self.state.restore_transaction_state(snapshot)
            state_restored = True
        except Exception as error:
            errors.append(error)

        if state_restored and restore_links is not None:
            try:
                self.transactions.restore_creation_history(restore_links)
            except Exception as error:
                errors.append(error)

        errors.extend(
            self._close_lease(
                lease,
                cancel=cancel,
                message=message,
            )
        )
        return tuple(errors)

    @staticmethod
    def _close_lease(
        lease: RuntimeOperationLease | None,
        *,
        cancel: bool,
        message: str,
    ) -> tuple[BaseException, ...]:
        if lease is None:
            return ()
        try:
            changed = (
                lease.cancel(message)
                if cancel
                else lease.fail(message)
            )
            if changed is not True:
                raise RuntimeError(
                    "Branch creation Undo lease was not finalized"
                )
        except Exception as error:
            return (error,)
        return ()

    @staticmethod
    def _fail_lease_or_raise(
        lease: RuntimeOperationLease | None,
        original_error: BaseException,
    ) -> None:
        if lease is None:
            return
        try:
            changed = lease.fail(str(original_error))
            if changed is not True:
                raise RuntimeError(
                    "Branch creation Undo lease was not finalized"
                )
        except Exception as finalization_error:
            raise BranchCreationExecutionError(
                original_error,
                (finalization_error,),
            ) from original_error

    @staticmethod
    def _finalize_committed_undo(
        lease: RuntimeOperationLease | None,
        transition: HistoryTransition,
    ) -> None:
        if lease is None:
            return
        try:
            changed = lease.succeed()
            if changed is not True:
                raise RuntimeError(
                    "Branch creation Undo lease was not finalized"
                )
        except Exception as error:
            raise BranchCreationHistoryCommittedError(
                transition,
                error,
            ) from error


__all__ = (
    "BranchCreationController",
    "BranchCreationExecutionError",
    "BranchCreationHistoryCommittedError",
    "BranchCreationStatePort",
)

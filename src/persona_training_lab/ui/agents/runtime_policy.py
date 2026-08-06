from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.operations import (
    OperationBlocker,
    ResourceClaim,
    RuntimeOperationLease,
)


@dataclass(frozen=True, slots=True)
class RuntimeBlockerState:
    blockers: tuple[OperationBlocker, ...]
    signature: tuple[tuple[str, str, str], ...]
    text: str


@dataclass(frozen=True, slots=True)
class RuntimeActionOverrides:
    make_current: bool | None = None
    compare: bool | None = None
    portrait: bool | None = None
    branch: bool | None = None
    delete: bool | None = None
    delete_reason_code: str = ""
    blocker_text: str = ""


class LineageRuntimePolicy:
    """Pure runtime decisions derived from lineage state and operation claims."""

    def __init__(self, safety: LineageRuntimeSafety | None) -> None:
        self._safety = safety

    def claims_for_node(
        self,
        node_id: str,
        *,
        is_custom: bool,
        projection_resources: Mapping[str, tuple[ResourceClaim, ...]],
    ) -> tuple[ResourceClaim, ...]:
        safety = self._safety
        if safety is not None and is_custom:
            inherited = safety.links_for_node(node_id)
            if inherited:
                return inherited
        return projection_resources.get(node_id, ())

    def blockers_for(self, node_ids: Iterable[str]) -> RuntimeBlockerState:
        safety = self._safety
        blockers = () if safety is None else safety.deletion_blockers(node_ids)
        signature = tuple(
            sorted(
                (
                    blocker.operation.operation_id,
                    blocker.claim.resource_kind,
                    blocker.claim.resource_id,
                )
                for blocker in blockers
            )
        )
        return RuntimeBlockerState(
            blockers=blockers,
            signature=signature,
            text=self.text_for_blockers(blockers),
        )

    def text_for_blockers(self, blockers: Iterable[OperationBlocker]) -> str:
        safety = self._safety
        return "" if safety is None else safety.blocker_text(blockers)

    def linked_resources(self, node_id: str) -> tuple[ResourceClaim, ...]:
        safety = self._safety
        return () if safety is None else safety.links_for_node(node_id)

    def action_overrides(
        self,
        *,
        node_kind: str,
        is_custom: bool,
        is_current: bool,
        is_archived: bool,
        subtree_ids: Iterable[str] = (),
    ) -> RuntimeActionOverrides:
        if node_kind == "model_version" and not is_custom:
            return RuntimeActionOverrides(
                make_current=not is_current and not is_archived,
                compare=not is_current,
                portrait=True,
                branch=not is_archived,
                delete=False,
                delete_reason_code="registered_model_version",
            )
        if not is_custom:
            return RuntimeActionOverrides()

        blocker_state = self.blockers_for(subtree_ids)
        if not blocker_state.blockers:
            return RuntimeActionOverrides()
        return RuntimeActionOverrides(
            delete=False,
            delete_reason_code="active_operation",
            blocker_text=blocker_state.text,
        )


class LineageBranchTransactions:
    """Persist branch resource inheritance and deletion leases atomically."""

    def __init__(self, safety: LineageRuntimeSafety | None) -> None:
        self._safety = safety

    def bind_child(
        self,
        child_node_id: str,
        parent_node_id: str,
        *,
        parent_is_custom: bool,
        fallback_claims: Iterable[ResourceClaim],
    ) -> tuple[ResourceClaim, ...]:
        safety = self._safety
        if safety is None or not child_node_id:
            return ()
        if parent_is_custom:
            return safety.inherit_node(
                child_node_id,
                parent_node_id,
                fallback_claims=fallback_claims,
            )
        return safety.bind_node(child_node_id, fallback_claims)

    def begin_deletion(
        self,
        node_ids: Iterable[str],
        *,
        subject_id: str,
    ) -> RuntimeOperationLease | None:
        safety = self._safety
        if safety is None:
            return None
        return safety.begin_deletion(node_ids, subject_id=subject_id)

    def forget(self, node_ids: Iterable[str]) -> int:
        safety = self._safety
        return 0 if safety is None else safety.forget_nodes(node_ids)

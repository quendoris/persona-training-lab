from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.operations import (
    OperationBlocker,
    ResourceClaim,
    RuntimeOperationLease,
)


_BRANCH_DELETE_HISTORY_KIND = "branch_delete_v1"


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

    def capture_deletion_history(
        self,
        node_ids: Iterable[str],
        *,
        subject_id: str,
    ) -> dict[str, Any]:
        safety = self._safety
        removed_ids = tuple(dict.fromkeys(item for item in node_ids if item))
        if safety is None or not subject_id or not removed_ids:
            return {}
        links: dict[str, list[dict[str, str]]] = {}
        for node_id in removed_ids:
            links[node_id] = [
                {
                    "resource_kind": claim.resource_kind,
                    "resource_id": claim.resource_id,
                    "access_mode": claim.access_mode,
                }
                for claim in safety.links_for_node(node_id)
            ]
        return {
            "kind": _BRANCH_DELETE_HISTORY_KIND,
            "subject_node_id": subject_id,
            "removed_ids": list(removed_ids),
            "resource_links": links,
        }

    def restore_deletion_history(
        self,
        metadata: Mapping[str, Any],
    ) -> tuple[str, ...]:
        safety = self._safety
        parsed = self._parse_deletion_history(metadata)
        if safety is None or parsed is None:
            return ()
        _, removed_ids, links = parsed
        safety.restore_node_links(links)
        return removed_ids

    def deletion_history_subject(
        self,
        metadata: Mapping[str, Any],
    ) -> str:
        parsed = self._parse_deletion_history(metadata)
        return "" if parsed is None else parsed[0]

    def deletion_history_removed_ids(
        self,
        metadata: Mapping[str, Any],
    ) -> tuple[str, ...]:
        parsed = self._parse_deletion_history(metadata)
        return () if parsed is None else parsed[1]

    def forget(self, node_ids: Iterable[str]) -> int:
        safety = self._safety
        return 0 if safety is None else safety.forget_nodes(node_ids)

    @staticmethod
    def _parse_deletion_history(
        metadata: Mapping[str, Any],
    ) -> tuple[
        str,
        tuple[str, ...],
        dict[str, tuple[ResourceClaim, ...]],
    ] | None:
        if metadata.get("kind") != _BRANCH_DELETE_HISTORY_KIND:
            return None
        subject_id = str(metadata.get("subject_node_id", "")).strip()
        raw_removed = metadata.get("removed_ids")
        if not isinstance(raw_removed, list):
            return None
        removed_ids = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in raw_removed
                if str(item).strip()
            )
        )
        if not subject_id or not removed_ids or subject_id not in removed_ids:
            return None

        raw_links = metadata.get("resource_links")
        if not isinstance(raw_links, dict):
            return None
        links: dict[str, tuple[ResourceClaim, ...]] = {}
        for node_id in removed_ids:
            raw_claims = raw_links.get(node_id, [])
            if not isinstance(raw_claims, list):
                return None
            claims: list[ResourceClaim] = []
            for raw_claim in raw_claims:
                if not isinstance(raw_claim, dict):
                    return None
                resource_kind = str(
                    raw_claim.get("resource_kind", "")
                ).strip()
                resource_id = str(
                    raw_claim.get("resource_id", "")
                ).strip()
                if not resource_kind or not resource_id:
                    return None
                claims.append(
                    ResourceClaim(
                        resource_kind,
                        resource_id,
                        str(raw_claim.get("access_mode", "read") or "read"),
                    )
                )
            links[node_id] = tuple(claims)
        return subject_id, removed_ids, links

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

from persona_training_lab.application.runtime.operations import (
    OperationBlocker,
    ResourceClaim,
    RuntimeOperationCoordinator,
    RuntimeOperationLease,
)


_PERSISTED_PROJECTION_IDS = frozenset(
    {"base", "dataset", "training", "snapshot", "portrait", "delta"}
)
_PERSISTED_PROJECTION_PREFIXES = (
    "base_model:",
    "persona_profile:",
    "dataset:",
    "training_run:",
    "artifact:",
    "model_version:",
    "evaluation_run:",
    "base:",
    "training:",
    "version:",
    "portrait:",
)


class LineageResourceLinksRepositoryPort(Protocol):
    def replace_links(
        self,
        node_id: str,
        claims: tuple[ResourceClaim, ...],
    ) -> None: ...

    def list_links(self, node_id: str) -> tuple[ResourceClaim, ...]: ...

    def delete_links(self, node_ids: tuple[str, ...]) -> int: ...


@dataclass(slots=True)
class LineageRuntimeSafety:
    repository: LineageResourceLinksRepositoryPort
    operations: RuntimeOperationCoordinator

    def bind_node(
        self,
        node_id: str,
        claims: Iterable[ResourceClaim],
    ) -> tuple[ResourceClaim, ...]:
        normalized = self._normalise_read_links(claims)
        if self.repository.list_links(node_id) != normalized:
            self.repository.replace_links(node_id, normalized)
        return normalized

    def reconcile_projection(
        self,
        claims_by_node: Mapping[str, Iterable[ResourceClaim]],
        previous_node_ids: Iterable[str] | None = None,
    ) -> tuple[str, ...]:
        """Replace one persisted projection link-set and forget stale nodes."""

        normalized = {
            node_id: self._normalise_read_links(claims)
            for node_id, claims in claims_by_node.items()
            if node_id
        }
        current_ids = tuple(sorted(normalized))
        current_set = set(current_ids)
        previous = (
            tuple(previous_node_ids)
            if previous_node_ids is not None
            else self._persisted_projection_node_ids()
        )
        stale_ids = tuple(
            node_id
            for node_id in dict.fromkeys(previous)
            if node_id and node_id not in current_set
        )
        reconciler = getattr(
            self.repository,
            "reconcile_projection_links",
            None,
        )
        if callable(reconciler):
            reconciler(normalized, stale_ids)
            return current_ids

        for node_id in current_ids:
            self.bind_node(node_id, normalized[node_id])
        self.forget_nodes(stale_ids)
        return current_ids

    def inherit_node(
        self,
        child_node_id: str,
        parent_node_id: str,
        *,
        fallback_claims: Iterable[ResourceClaim] = (),
    ) -> tuple[ResourceClaim, ...]:
        inherited = self.repository.list_links(parent_node_id)
        if not inherited:
            inherited = self._normalise_read_links(fallback_claims)
        if self.repository.list_links(child_node_id) != inherited:
            self.repository.replace_links(child_node_id, inherited)
        return inherited

    def links_for_node(self, node_id: str) -> tuple[ResourceClaim, ...]:
        return self.repository.list_links(node_id)

    def claims_for_nodes(
        self,
        node_ids: Iterable[str],
    ) -> tuple[ResourceClaim, ...]:
        unique: dict[tuple[str, str], ResourceClaim] = {}
        for node_id in dict.fromkeys(item for item in node_ids if item):
            lineage_claim = ResourceClaim("lineage_node", node_id, "write")
            unique[lineage_claim.key] = lineage_claim
            for claim in self.repository.list_links(node_id):
                destructive = ResourceClaim(
                    claim.resource_kind,
                    claim.resource_id,
                    "write",
                )
                unique[destructive.key] = destructive
        return tuple(sorted(unique.values()))

    def deletion_blockers(
        self,
        node_ids: Iterable[str],
    ) -> tuple[OperationBlocker, ...]:
        return self.operations.deletion_blockers(
            self.claims_for_nodes(node_ids)
        )

    def begin_deletion(
        self,
        node_ids: Iterable[str],
        *,
        subject_id: str,
    ) -> RuntimeOperationLease:
        claims = self.claims_for_nodes(node_ids)
        return self.operations.begin(
            operation_kind="lineage_delete",
            subject_kind="lineage_subtree",
            subject_id=subject_id,
            claims=claims,
        )

    def forget_nodes(self, node_ids: Iterable[str]) -> int:
        unique = tuple(dict.fromkeys(item for item in node_ids if item))
        if not unique:
            return 0
        return self.repository.delete_links(unique)

    @staticmethod
    def blocker_text(blockers: Iterable[OperationBlocker]) -> str:
        unique: list[str] = []
        for blocker in blockers:
            operation = blocker.operation.operation_kind
            subject = blocker.operation.subject_id
            resource = (
                f"{blocker.claim.resource_kind}="
                f"{blocker.claim.resource_id}"
            )
            text = f"{operation} · {subject} · {resource}"
            if text not in unique:
                unique.append(text)
        return "; ".join(unique)

    def _persisted_projection_node_ids(self) -> tuple[str, ...]:
        reader = getattr(self.repository, "list_node_ids", None)
        if not callable(reader):
            return ()
        return tuple(
            node_id
            for node_id in reader()
            if self._is_persisted_projection_id(node_id)
        )

    @staticmethod
    def _is_persisted_projection_id(node_id: str) -> bool:
        return node_id in _PERSISTED_PROJECTION_IDS or node_id.startswith(
            _PERSISTED_PROJECTION_PREFIXES
        )

    @staticmethod
    def _normalise_read_links(
        claims: Iterable[ResourceClaim],
    ) -> tuple[ResourceClaim, ...]:
        unique: dict[tuple[str, str], ResourceClaim] = {}
        for claim in claims:
            if claim.resource_kind == "lineage_node":
                continue
            read_claim = ResourceClaim(
                claim.resource_kind,
                claim.resource_id,
                "read",
            )
            unique[read_claim.key] = read_claim
        return tuple(sorted(unique.values()))

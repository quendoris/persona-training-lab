from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from persona_training_lab.application.runtime.operations import (
    OperationBlocker,
    ResourceClaim,
    RuntimeOperationCoordinator,
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
                # Destructive checks do not care about read/write semantics, but
                # write expresses that the referenced entity would be affected.
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

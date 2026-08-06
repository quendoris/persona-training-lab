from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from persona_training_lab.application.runtime.operations import ResourceClaim


_CLAIM_CONTEXT_FIELDS: Mapping[str, str] = MappingProxyType(
    {
        "model_version": "model_version_id",
        "artifact_path": "artifact_path",
        "training_run": "training_run_id",
        "dataset": "dataset_title",
        "profile": "profile_title",
        "model_definition": "base_model",
    }
)


@dataclass(frozen=True, slots=True)
class LineageNavigationRequest:
    workspace_key: str
    payload: Mapping[str, object]

    def mutable_payload(self) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in self.payload.items():
            if isinstance(value, Mapping):
                result[key] = dict(value)
            else:
                result[key] = value
        return result


class LineageContextRouter:
    """Build immutable lineage context and explicit workspace requests."""

    def node_context(
        self,
        node_id: str,
        *,
        base_context: Mapping[str, str] | None = None,
        node_title: str = "",
        node_status: str = "",
        claims: Iterable[ResourceClaim] = (),
    ) -> Mapping[str, str]:
        context = dict(base_context or {})
        context["node_id"] = node_id
        if node_title:
            context.setdefault("node_title", node_title)
        if node_status:
            context.setdefault("node_status", node_status)

        for claim in claims:
            field = _CLAIM_CONTEXT_FIELDS.get(claim.resource_kind)
            if field:
                context.setdefault(field, claim.resource_id)
        return MappingProxyType(context)

    def request(
        self,
        workspace_key: str,
        *,
        selected: Mapping[str, str],
        current: Mapping[str, str],
    ) -> LineageNavigationRequest:
        if workspace_key == "analysis":
            payload: Mapping[str, object] = MappingProxyType(
                {
                    "selected": MappingProxyType(dict(selected)),
                    "current": MappingProxyType(dict(current)),
                }
            )
        else:
            payload = MappingProxyType(dict(selected))
        return LineageNavigationRequest(workspace_key, payload)


__all__ = ("LineageContextRouter", "LineageNavigationRequest")

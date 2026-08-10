from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentDetailView,
    AgentText,
)


@dataclass(slots=True, frozen=True)
class ProjectedVersionNode:
    node_id: str
    depth: int
    title: AgentText
    subtitle: AgentText
    status: AgentText
    tone: str = "neutral"
    branch_note: str = "main"
    parent_id: str | None = None


@dataclass(slots=True, frozen=True)
class LineagePresentationProjection:
    nodes: tuple[ProjectedVersionNode, ...]
    details: dict[str, AgentDetailView]
    resources: dict[str, tuple[ResourceClaim, ...]]
    entity_context: dict[str, dict[str, str]]
    signature: tuple[tuple[str, str, str, str], ...]


# Compatibility type name retained while callers migrate to the semantic name.
RealLineageProjection = LineagePresentationProjection

__all__ = (
    "LineagePresentationProjection",
    "ProjectedVersionNode",
    "RealLineageProjection",
)

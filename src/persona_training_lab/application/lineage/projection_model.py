from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping
from urllib.parse import quote

from persona_training_lab.application.runtime.operations import ResourceClaim


class LineageEntityKind(StrEnum):
    BASE_MODEL = "base_model"
    PERSONA_PROFILE = "persona_profile"
    DATASET = "dataset"
    TRAINING_RUN = "training_run"
    ARTIFACT = "artifact"
    MODEL_VERSION = "model_version"
    EVALUATION_RUN = "evaluation_run"


class LineageState(StrEnum):
    UNKNOWN = "unknown"
    PENDING = "pending"
    RUNNING = "running"
    READY = "ready"
    PARTIAL = "partial"
    FAILED = "failed"
    ARCHIVED = "archived"


class LineageRelation(StrEnum):
    USES_BASE_MODEL = "uses_base_model"
    USES_PROFILE = "uses_profile"
    USES_DATASET = "uses_dataset"
    PRODUCES_ARTIFACT = "produces_artifact"
    PRODUCES_VERSION = "produces_version"
    BACKS_VERSION = "backs_version"
    EVALUATES_VERSION = "evaluates_version"
    SUPPLIES_EVALUATION = "supplies_evaluation"


class LineageSource(StrEnum):
    DATASETS = "datasets"
    TRAINING = "training"
    MODEL_VERSIONS = "model_versions"
    EXPERIMENTS = "experiments"


@dataclass(frozen=True, slots=True)
class LineageNode:
    node_id: str
    kind: LineageEntityKind
    entity_id: str
    state: LineageState = LineageState.UNKNOWN
    attributes: Mapping[str, str] = field(default_factory=dict)
    claims: tuple[ResourceClaim, ...] = ()

    def __post_init__(self) -> None:
        node_id = self.node_id.strip()
        entity_id = self.entity_id.strip()
        if not node_id:
            raise ValueError("node_id must not be empty")
        if not entity_id:
            raise ValueError("entity_id must not be empty")
        normalized_attributes = {
            str(key).strip(): str(value)
            for key, value in self.attributes.items()
            if str(key).strip()
        }
        object.__setattr__(self, "node_id", node_id)
        object.__setattr__(self, "entity_id", entity_id)
        object.__setattr__(
            self,
            "attributes",
            MappingProxyType(normalized_attributes),
        )
        object.__setattr__(
            self,
            "claims",
            tuple(sorted(set(self.claims))),
        )


@dataclass(frozen=True, slots=True, order=True)
class LineageEdge:
    source_node_id: str
    target_node_id: str
    relation: LineageRelation

    def __post_init__(self) -> None:
        source = self.source_node_id.strip()
        target = self.target_node_id.strip()
        if not source or not target:
            raise ValueError("lineage edge endpoints must not be empty")
        if source == target:
            raise ValueError("lineage self-edges are not allowed")
        object.__setattr__(self, "source_node_id", source)
        object.__setattr__(self, "target_node_id", target)


@dataclass(frozen=True, slots=True, order=True)
class UnresolvedLineageDependency:
    dependent_node_id: str
    expected_kind: LineageEntityKind
    reference: str
    relation: LineageRelation
    reason_code: str


@dataclass(frozen=True, slots=True, order=True)
class LineageSourceFailure:
    source: LineageSource
    error_type: str


@dataclass(frozen=True, slots=True)
class LineageProjection:
    nodes: tuple[LineageNode, ...]
    edges: tuple[LineageEdge, ...]
    unresolved: tuple[UnresolvedLineageDependency, ...]
    source_failures: tuple[LineageSourceFailure, ...]
    topology_revision: str
    content_revision: str

    def node(self, node_id: str) -> LineageNode | None:
        return next(
            (item for item in self.nodes if item.node_id == node_id),
            None,
        )

    def incoming(self, node_id: str) -> tuple[LineageEdge, ...]:
        return tuple(
            edge for edge in self.edges if edge.target_node_id == node_id
        )

    def outgoing(self, node_id: str) -> tuple[LineageEdge, ...]:
        return tuple(
            edge for edge in self.edges if edge.source_node_id == node_id
        )


def lineage_node_id(kind: LineageEntityKind, entity_id: str) -> str:
    clean = entity_id.strip()
    if not clean:
        raise ValueError("entity_id must not be empty")
    encoded = quote(clean, safe="._-")
    if len(encoded) > 160:
        encoded = "sha256-" + sha256(clean.encode("utf-8")).hexdigest()
    return f"{kind.value}:{encoded}"


__all__ = (
    "LineageEdge",
    "LineageEntityKind",
    "LineageNode",
    "LineageProjection",
    "LineageRelation",
    "LineageSource",
    "LineageSourceFailure",
    "LineageState",
    "UnresolvedLineageDependency",
    "lineage_node_id",
)

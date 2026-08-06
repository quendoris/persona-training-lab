from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Iterable, Mapping
from urllib.parse import quote

from persona_training_lab.application.datasets.status_mapping import (
    normalize_dataset_status,
)
from persona_training_lab.application.experiments.portrait import (
    parse_portrait_payload,
)
from persona_training_lab.application.experiments.status_mapping import (
    normalize_evaluation_status,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.domain.datasets.statuses import DatasetVersionStatus
from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus
from persona_training_lab.domain.models.statuses import ModelVersionStatus
from persona_training_lab.domain.training.statuses import TrainingRunStatus


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


@dataclass(slots=True)
class LineageProjectionService:
    datasets_service: object | None = None
    training_service: object | None = None
    model_versions_service: object | None = None
    experiments_service: object | None = None

    def build_projection(self) -> LineageProjection:
        failures: list[LineageSourceFailure] = []
        datasets = self._read_source(
            self.datasets_service,
            "list_datasets",
            LineageSource.DATASETS,
            failures,
        )
        runs = self._read_source(
            self.training_service,
            "list_training_runs",
            LineageSource.TRAINING,
            failures,
        )
        versions = self._read_source(
            self.model_versions_service,
            "list_model_versions",
            LineageSource.MODEL_VERSIONS,
            failures,
        )
        experiments = self._read_source(
            self.experiments_service,
            "list_experiments",
            LineageSource.EXPERIMENTS,
            failures,
        )

        builder = _ProjectionBuilder()
        dataset_index = self._add_datasets(builder, datasets)
        run_index = self._add_training_runs(
            builder,
            runs,
            dataset_index,
        )
        version_index = self._add_model_versions(
            builder,
            versions,
            run_index,
        )
        self._add_evaluations(
            builder,
            experiments,
            version_index,
        )
        return builder.freeze(tuple(sorted(failures)))

    @staticmethod
    def _read_source(
        source: object | None,
        method_name: str,
        source_name: LineageSource,
        failures: list[LineageSourceFailure],
    ) -> tuple[object, ...]:
        if source is None:
            return ()
        method = getattr(source, method_name, None)
        if not callable(method):
            failures.append(
                LineageSourceFailure(source_name, "missing_reader")
            )
            return ()
        try:
            return tuple(method())
        except Exception as error:
            failures.append(
                LineageSourceFailure(
                    source_name,
                    type(error).__name__,
                )
            )
            return ()

    @staticmethod
    def _add_datasets(
        builder: _ProjectionBuilder,
        datasets: Iterable[object],
    ) -> _DatasetIndex:
        by_id: dict[str, str] = {}
        by_title: dict[str, list[str]] = {}
        for item in datasets:
            dataset_id = _value(item, "dataset_id")
            if not dataset_id:
                continue
            title = _value(item, "title")
            status = getattr(item, "status_code", None)
            if not isinstance(status, DatasetVersionStatus):
                status = normalize_dataset_status(
                    _value(item, "status")
                )
            node = LineageNode(
                node_id=lineage_node_id(
                    LineageEntityKind.DATASET,
                    dataset_id,
                ),
                kind=LineageEntityKind.DATASET,
                entity_id=dataset_id,
                state=_dataset_state(status),
                attributes={
                    "title": title,
                    "status": _value(item, "status"),
                    "path": _value(item, "path"),
                    "format": _value(item, "format"),
                    "record_count": _value(item, "record_count"),
                    "valid_count": _value(item, "valid_count"),
                    "invalid_count": _value(item, "invalid_count"),
                },
                claims=(ResourceClaim("dataset", dataset_id),),
            )
            builder.add_node(node)
            by_id[dataset_id] = node.node_id
            if title:
                by_title.setdefault(_reference_key(title), []).append(
                    node.node_id
                )
        return _DatasetIndex(
            by_id=MappingProxyType(by_id),
            by_title=MappingProxyType(
                {
                    key: tuple(sorted(values))
                    for key, values in by_title.items()
                }
            ),
        )

    @staticmethod
    def _add_training_runs(
        builder: _ProjectionBuilder,
        runs: Iterable[object],
        datasets: _DatasetIndex,
    ) -> Mapping[str, str]:
        run_index: dict[str, str] = {}
        for item in runs:
            run_id = _value(item, "run_id")
            if not run_id:
                continue
            status = getattr(item, "status_code", TrainingRunStatus.UNKNOWN)
            if not isinstance(status, TrainingRunStatus):
                status = TrainingRunStatus.UNKNOWN
            run_node = LineageNode(
                node_id=lineage_node_id(
                    LineageEntityKind.TRAINING_RUN,
                    run_id,
                ),
                kind=LineageEntityKind.TRAINING_RUN,
                entity_id=run_id,
                state=_training_state(status),
                attributes={
                    "title": _value(item, "title"),
                    "status": _value(item, "status"),
                    "mode": _value(item, "mode"),
                    "progress": _value(item, "progress"),
                    "epoch_progress": _value(item, "epoch_progress"),
                    "loss": _value(item, "loss"),
                    "artifact_path": _value(item, "artifact_path"),
                },
                claims=(ResourceClaim("training_run", run_id),),
            )
            builder.add_node(run_node)
            run_index[run_id] = run_node.node_id

            base_model = _value(item, "base_model")
            if base_model:
                base_node = _reference_node(
                    LineageEntityKind.BASE_MODEL,
                    base_model,
                    ResourceClaim("model_definition", base_model),
                )
                builder.add_node(base_node)
                builder.add_edge(
                    base_node.node_id,
                    run_node.node_id,
                    LineageRelation.USES_BASE_MODEL,
                )
            else:
                builder.add_unresolved(
                    run_node.node_id,
                    LineageEntityKind.BASE_MODEL,
                    "",
                    LineageRelation.USES_BASE_MODEL,
                    "missing_reference",
                )

            profile = _value(item, "profile")
            if profile:
                profile_node = _reference_node(
                    LineageEntityKind.PERSONA_PROFILE,
                    profile,
                    ResourceClaim("profile", profile),
                )
                builder.add_node(profile_node)
                builder.add_edge(
                    profile_node.node_id,
                    run_node.node_id,
                    LineageRelation.USES_PROFILE,
                )
            else:
                builder.add_unresolved(
                    run_node.node_id,
                    LineageEntityKind.PERSONA_PROFILE,
                    "",
                    LineageRelation.USES_PROFILE,
                    "missing_reference",
                )

            dataset_reference = _value(item, "dataset_version")
            dataset_node_id, reason = datasets.resolve(dataset_reference)
            if dataset_node_id:
                builder.add_edge(
                    dataset_node_id,
                    run_node.node_id,
                    LineageRelation.USES_DATASET,
                )
            else:
                builder.add_unresolved(
                    run_node.node_id,
                    LineageEntityKind.DATASET,
                    dataset_reference,
                    LineageRelation.USES_DATASET,
                    reason,
                )

            artifact_path = _value(item, "artifact_path")
            if artifact_path:
                artifact_node = _artifact_node(artifact_path)
                builder.add_node(artifact_node)
                builder.add_edge(
                    run_node.node_id,
                    artifact_node.node_id,
                    LineageRelation.PRODUCES_ARTIFACT,
                )
        return MappingProxyType(run_index)

    @staticmethod
    def _add_model_versions(
        builder: _ProjectionBuilder,
        versions: Iterable[object],
        runs: Mapping[str, str],
    ) -> Mapping[str, str]:
        version_index: dict[str, str] = {}
        for item in versions:
            version_id = _value(item, "version_id")
            if not version_id:
                continue
            status = getattr(item, "status_code", ModelVersionStatus.UNKNOWN)
            if not isinstance(status, ModelVersionStatus):
                status = ModelVersionStatus.UNKNOWN
            version_node = LineageNode(
                node_id=lineage_node_id(
                    LineageEntityKind.MODEL_VERSION,
                    version_id,
                ),
                kind=LineageEntityKind.MODEL_VERSION,
                entity_id=version_id,
                state=_model_version_state(status),
                attributes={
                    "title": _value(item, "title"),
                    "status": _value(item, "status"),
                    "training_run_id": _value(item, "training_run_id"),
                    "artifact_path": _value(item, "artifact_path"),
                    "base_model": _value(item, "base_model"),
                    "profile_title": _value(item, "profile_title"),
                    "dataset_title": _value(item, "dataset_title"),
                    "quality_summary": _value(item, "quality_summary"),
                },
                claims=(ResourceClaim("model_version", version_id),),
            )
            builder.add_node(version_node)
            version_index[version_id] = version_node.node_id

            run_id = _value(item, "training_run_id")
            run_node_id = runs.get(run_id)
            if run_node_id:
                builder.add_edge(
                    run_node_id,
                    version_node.node_id,
                    LineageRelation.PRODUCES_VERSION,
                )
            else:
                builder.add_unresolved(
                    version_node.node_id,
                    LineageEntityKind.TRAINING_RUN,
                    run_id,
                    LineageRelation.PRODUCES_VERSION,
                    (
                        "missing_reference"
                        if not run_id
                        else "unknown_reference"
                    ),
                )

            artifact_path = _value(item, "artifact_path")
            if artifact_path:
                artifact_node = _artifact_node(artifact_path)
                builder.add_node(artifact_node)
                builder.add_edge(
                    artifact_node.node_id,
                    version_node.node_id,
                    LineageRelation.BACKS_VERSION,
                )
        return MappingProxyType(version_index)

    @staticmethod
    def _add_evaluations(
        builder: _ProjectionBuilder,
        experiments: Iterable[object],
        versions: Mapping[str, str],
    ) -> None:
        for item in experiments:
            experiment_id = _value(item, "experiment_id")
            if not experiment_id:
                continue
            record = parse_portrait_payload(_value(item, "subtitle"))
            status = getattr(item, "status_code", None)
            if not isinstance(status, EvaluationRunStatus):
                status = normalize_evaluation_status(
                    _value(item, "status")
                )
            evaluation_node = LineageNode(
                node_id=lineage_node_id(
                    LineageEntityKind.EVALUATION_RUN,
                    experiment_id,
                ),
                kind=LineageEntityKind.EVALUATION_RUN,
                entity_id=experiment_id,
                state=_evaluation_state(status),
                attributes={
                    "title": _value(item, "title"),
                    "status": _value(item, "status"),
                    "model_version_id": record.model_version_id,
                    "artifact_path": record.artifact_path,
                    "battery_version": record.battery_version,
                    "scoring_version": record.scoring_version,
                    "passed": str(record.passed),
                    "total": str(record.total),
                    "invalid_count": str(record.invalid_count),
                },
                claims=(ResourceClaim("experiment", experiment_id),),
            )
            builder.add_node(evaluation_node)

            version_id = record.model_version_id
            version_node_id = versions.get(version_id)
            if version_node_id:
                builder.add_edge(
                    version_node_id,
                    evaluation_node.node_id,
                    LineageRelation.EVALUATES_VERSION,
                )
            else:
                builder.add_unresolved(
                    evaluation_node.node_id,
                    LineageEntityKind.MODEL_VERSION,
                    version_id,
                    LineageRelation.EVALUATES_VERSION,
                    (
                        "missing_reference"
                        if not version_id
                        else "unknown_reference"
                    ),
                )

            if record.artifact_path:
                artifact_node = _artifact_node(record.artifact_path)
                builder.add_node(artifact_node)
                builder.add_edge(
                    artifact_node.node_id,
                    evaluation_node.node_id,
                    LineageRelation.SUPPLIES_EVALUATION,
                )


@dataclass(frozen=True, slots=True)
class _DatasetIndex:
    by_id: Mapping[str, str]
    by_title: Mapping[str, tuple[str, ...]]

    def resolve(self, reference: str) -> tuple[str, str]:
        clean = reference.strip()
        if not clean:
            return "", "missing_reference"
        direct = self.by_id.get(clean)
        if direct:
            return direct, ""
        matches = self.by_title.get(_reference_key(clean), ())
        if len(matches) == 1:
            return matches[0], ""
        if len(matches) > 1:
            return "", "ambiguous_reference"
        return "", "unknown_reference"


class _ProjectionBuilder:
    _STATE_PRIORITY = {
        LineageState.UNKNOWN: 0,
        LineageState.PENDING: 1,
        LineageState.RUNNING: 2,
        LineageState.READY: 3,
        LineageState.ARCHIVED: 4,
        LineageState.PARTIAL: 5,
        LineageState.FAILED: 6,
    }

    def __init__(self) -> None:
        self._nodes: dict[str, LineageNode] = {}
        self._edges: set[LineageEdge] = set()
        self._unresolved: set[UnresolvedLineageDependency] = set()

    def add_node(self, node: LineageNode) -> None:
        existing = self._nodes.get(node.node_id)
        if existing is None:
            self._nodes[node.node_id] = node
            return
        if existing.kind is not node.kind or existing.entity_id != node.entity_id:
            raise ValueError(
                f"Conflicting lineage node identity: {node.node_id}"
            )
        attributes = dict(existing.attributes)
        attributes.update(
            {
                key: value
                for key, value in node.attributes.items()
                if value and not attributes.get(key)
            }
        )
        state = max(
            (existing.state, node.state),
            key=self._STATE_PRIORITY.__getitem__,
        )
        self._nodes[node.node_id] = LineageNode(
            node_id=node.node_id,
            kind=node.kind,
            entity_id=node.entity_id,
            state=state,
            attributes=attributes,
            claims=tuple(sorted(set(existing.claims) | set(node.claims))),
        )

    def add_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        relation: LineageRelation,
    ) -> None:
        if source_node_id not in self._nodes:
            raise ValueError(f"Unknown source lineage node: {source_node_id}")
        if target_node_id not in self._nodes:
            raise ValueError(f"Unknown target lineage node: {target_node_id}")
        self._edges.add(
            LineageEdge(source_node_id, target_node_id, relation)
        )

    def add_unresolved(
        self,
        dependent_node_id: str,
        expected_kind: LineageEntityKind,
        reference: str,
        relation: LineageRelation,
        reason_code: str,
    ) -> None:
        self._unresolved.add(
            UnresolvedLineageDependency(
                dependent_node_id=dependent_node_id,
                expected_kind=expected_kind,
                reference=reference.strip(),
                relation=relation,
                reason_code=reason_code,
            )
        )

    def freeze(
        self,
        failures: tuple[LineageSourceFailure, ...],
    ) -> LineageProjection:
        nodes = tuple(sorted(self._nodes.values(), key=lambda item: item.node_id))
        edges = tuple(sorted(self._edges))
        unresolved = tuple(sorted(self._unresolved))
        topology_payload = {
            "nodes": [
                (node.node_id, node.kind.value, node.entity_id)
                for node in nodes
            ],
            "edges": [
                (
                    edge.source_node_id,
                    edge.target_node_id,
                    edge.relation.value,
                )
                for edge in edges
            ],
            "unresolved": [
                (
                    item.dependent_node_id,
                    item.expected_kind.value,
                    item.reference,
                    item.relation.value,
                    item.reason_code,
                )
                for item in unresolved
            ],
        }
        content_payload = {
            **topology_payload,
            "node_content": [
                (
                    node.node_id,
                    node.state.value,
                    sorted(node.attributes.items()),
                    [
                        (
                            claim.resource_kind,
                            claim.resource_id,
                            claim.access_mode,
                        )
                        for claim in node.claims
                    ],
                )
                for node in nodes
            ],
            "failures": [
                (item.source.value, item.error_type)
                for item in failures
            ],
        }
        return LineageProjection(
            nodes=nodes,
            edges=edges,
            unresolved=unresolved,
            source_failures=failures,
            topology_revision=_revision(topology_payload),
            content_revision=_revision(content_payload),
        )


def lineage_node_id(kind: LineageEntityKind, entity_id: str) -> str:
    clean = entity_id.strip()
    if not clean:
        raise ValueError("entity_id must not be empty")
    encoded = quote(clean, safe="._-")
    if len(encoded) > 160:
        encoded = "sha256-" + sha256(clean.encode("utf-8")).hexdigest()
    return f"{kind.value}:{encoded}"


def _reference_node(
    kind: LineageEntityKind,
    reference: str,
    claim: ResourceClaim,
) -> LineageNode:
    return LineageNode(
        node_id=lineage_node_id(kind, reference),
        kind=kind,
        entity_id=reference,
        state=LineageState.READY,
        attributes={"reference": reference},
        claims=(claim,),
    )


def _artifact_node(path: str) -> LineageNode:
    return LineageNode(
        node_id=lineage_node_id(LineageEntityKind.ARTIFACT, path),
        kind=LineageEntityKind.ARTIFACT,
        entity_id=path,
        state=LineageState.READY,
        attributes={"path": path},
        claims=(ResourceClaim("artifact_path", path),),
    )


def _value(item: object, name: str) -> str:
    value = getattr(item, name, "")
    return str(value if value is not None else "").strip()


def _reference_key(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _training_state(status: TrainingRunStatus) -> LineageState:
    return {
        TrainingRunStatus.CREATED: LineageState.PENDING,
        TrainingRunStatus.READY: LineageState.PENDING,
        TrainingRunStatus.RUNNING: LineageState.RUNNING,
        TrainingRunStatus.FAILED: LineageState.FAILED,
        TrainingRunStatus.COMPLETED: LineageState.READY,
    }.get(status, LineageState.UNKNOWN)


def _dataset_state(status: DatasetVersionStatus) -> LineageState:
    return {
        DatasetVersionStatus.DRAFT: LineageState.PENDING,
        DatasetVersionStatus.IMPORTED: LineageState.PENDING,
        DatasetVersionStatus.VALIDATED: LineageState.READY,
        DatasetVersionStatus.APPROVED: LineageState.READY,
        DatasetVersionStatus.ARCHIVED: LineageState.ARCHIVED,
    }.get(status, LineageState.UNKNOWN)


def _model_version_state(status: ModelVersionStatus) -> LineageState:
    return {
        ModelVersionStatus.DRAFT: LineageState.PENDING,
        ModelVersionStatus.READY: LineageState.READY,
        ModelVersionStatus.ARCHIVED: LineageState.ARCHIVED,
        ModelVersionStatus.FAILED: LineageState.FAILED,
    }.get(status, LineageState.UNKNOWN)


def _evaluation_state(status: EvaluationRunStatus) -> LineageState:
    return {
        EvaluationRunStatus.CREATED: LineageState.PENDING,
        EvaluationRunStatus.RUNNING: LineageState.RUNNING,
        EvaluationRunStatus.PARTIAL: LineageState.PARTIAL,
        EvaluationRunStatus.FAILED: LineageState.FAILED,
        EvaluationRunStatus.COMPLETED: LineageState.READY,
    }.get(status, LineageState.UNKNOWN)


def _revision(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()

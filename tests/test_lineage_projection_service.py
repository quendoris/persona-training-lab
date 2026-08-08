from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.application.lineage import (
    atomic_projection as atomic_projection_module,
)
from persona_training_lab.application.lineage.projection import (
    LineageEntityKind,
    LineageProjectionService,
    LineageRelation,
    LineageSource,
    LineageState,
    lineage_node_id,
)
from persona_training_lab.application.lineage.projection_builder import (
    build_lineage_projection,
)
from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus
from persona_training_lab.domain.models.statuses import ModelVersionStatus
from persona_training_lab.domain.training.statuses import TrainingRunStatus


class _Datasets:
    def __init__(self, items=(), *, error: Exception | None = None) -> None:
        self.items = list(items)
        self.error = error
        self.calls = 0

    def list_datasets(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return list(self.items)


class _Training:
    def __init__(self, items=(), *, error: Exception | None = None) -> None:
        self.items = list(items)
        self.error = error
        self.calls = 0

    def list_training_runs(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return list(self.items)


class _Versions:
    def __init__(self, items=(), *, error: Exception | None = None) -> None:
        self.items = list(items)
        self.error = error
        self.calls = 0

    def list_model_versions(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return list(self.items)


class _Experiments:
    def __init__(self, items=(), *, error: Exception | None = None) -> None:
        self.items = list(items)
        self.error = error
        self.calls = 0

    def list_experiments(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return list(self.items)


def _dataset(
    dataset_id: str,
    title: str,
    *,
    status: str = "Одобрен для обучения",
):
    return SimpleNamespace(
        dataset_id=dataset_id,
        title=title,
        status=status,
        path=f"/datasets/{dataset_id}.jsonl",
        format="jsonl",
        record_count=100,
        valid_count=100,
        invalid_count=0,
    )


def _run(
    run_id: str,
    *,
    dataset: str = "Dataset A",
    status: TrainingRunStatus = TrainingRunStatus.COMPLETED,
    artifact: str | None = None,
):
    artifact_path = artifact if artifact is not None else f"/artifacts/{run_id}"
    return SimpleNamespace(
        run_id=run_id,
        title=f"Training {run_id}",
        status=status.value,
        status_code=status,
        base_model="Qwen Base",
        profile="Mia Core",
        dataset_version=dataset,
        mode="full",
        progress="1",
        epoch_progress="3/3",
        loss="0.42",
        artifact_path=artifact_path,
    )


def _version(
    version_id: str,
    run_id: str,
    *,
    status: ModelVersionStatus = ModelVersionStatus.READY,
    artifact: str | None = None,
):
    artifact_path = artifact if artifact is not None else f"/artifacts/{run_id}"
    return SimpleNamespace(
        version_id=version_id,
        title=f"Version {version_id}",
        status=status.value,
        status_code=status,
        training_run_id=run_id,
        artifact_path=artifact_path,
        base_model="Qwen Base",
        profile_title="Mia Core",
        dataset_title="Dataset A",
        quality_summary="loss 0.42",
    )


def _experiment(
    experiment_id: str,
    version_id: str,
    *,
    artifact: str | None = None,
):
    artifact_path = artifact if artifact is not None else "/artifacts/trn_001"
    return SimpleNamespace(
        experiment_id=experiment_id,
        title=f"Portrait {experiment_id}",
        status="completed",
        status_code=EvaluationRunStatus.COMPLETED,
        subtitle=(
            "PORTRAIT: 1/1 Big Five items · "
            f"model_version={version_id} · artifact={artifact_path} · "
            "battery=v1 · scoring=s1\n\n"
            "CASE 1\nTRAIT: Openness\nKEY: O1\nREVERSE: 0\n"
            "STATUS: Model responds\nVALID_SCORE: 1\n"
            "RESPONSE: SCORE: 5"
        ),
    )


def _edge_set(projection):
    return {
        (edge.source_node_id, edge.target_node_id, edge.relation)
        for edge in projection.edges
    }


def test_service_adapter_matches_pure_projection_builder() -> None:
    datasets = [_dataset("ds_001", "Dataset A")]
    runs = [_run("trn_001")]
    versions = [_version("mdl_001", "trn_001")]
    experiments = [_experiment("evr_001", "mdl_001")]

    direct = build_lineage_projection(
        datasets=datasets,
        training_runs=runs,
        model_versions=versions,
        evaluations=experiments,
    )
    through_services = LineageProjectionService(
        datasets_service=_Datasets(datasets),
        training_service=_Training(runs),
        model_versions_service=_Versions(versions),
        experiments_service=_Experiments(experiments),
    ).build_projection()

    assert through_services == direct


def test_atomic_projection_uses_pure_builder_without_fake_sources() -> None:
    assert atomic_projection_module.build_lineage_projection is build_lineage_projection
    assert not hasattr(atomic_projection_module, "_StaticSource")


def test_projection_builds_exact_dag_and_reads_each_source_once() -> None:
    datasets = _Datasets([_dataset("ds_001", "Dataset A")])
    training = _Training([_run("trn_001")])
    versions = _Versions([_version("mdl_001", "trn_001")])
    experiments = _Experiments([_experiment("evr_001", "mdl_001")])
    service = LineageProjectionService(
        datasets_service=datasets,
        training_service=training,
        model_versions_service=versions,
        experiments_service=experiments,
    )

    projection = service.build_projection()

    assert datasets.calls == 1
    assert training.calls == 1
    assert versions.calls == 1
    assert experiments.calls == 1
    assert projection.source_failures == ()
    assert projection.unresolved == ()

    dataset_id = lineage_node_id(LineageEntityKind.DATASET, "ds_001")
    run_id = lineage_node_id(LineageEntityKind.TRAINING_RUN, "trn_001")
    version_id = lineage_node_id(LineageEntityKind.MODEL_VERSION, "mdl_001")
    evaluation_id = lineage_node_id(
        LineageEntityKind.EVALUATION_RUN,
        "evr_001",
    )
    artifact_id = lineage_node_id(
        LineageEntityKind.ARTIFACT,
        "/artifacts/trn_001",
    )
    base_id = lineage_node_id(
        LineageEntityKind.BASE_MODEL,
        "Qwen Base",
    )
    profile_id = lineage_node_id(
        LineageEntityKind.PERSONA_PROFILE,
        "Mia Core",
    )

    assert projection.node(run_id).state is LineageState.READY
    assert projection.node(version_id).state is LineageState.READY
    assert projection.node(evaluation_id).state is LineageState.READY
    assert len(
        [
            node
            for node in projection.nodes
            if node.kind is LineageEntityKind.ARTIFACT
        ]
    ) == 1

    edges = _edge_set(projection)
    assert (base_id, run_id, LineageRelation.USES_BASE_MODEL) in edges
    assert (profile_id, run_id, LineageRelation.USES_PROFILE) in edges
    assert (dataset_id, run_id, LineageRelation.USES_DATASET) in edges
    assert (run_id, artifact_id, LineageRelation.PRODUCES_ARTIFACT) in edges
    assert (run_id, version_id, LineageRelation.PRODUCES_VERSION) in edges
    assert (artifact_id, version_id, LineageRelation.BACKS_VERSION) in edges
    assert (
        version_id,
        evaluation_id,
        LineageRelation.EVALUATES_VERSION,
    ) in edges
    assert (
        artifact_id,
        evaluation_id,
        LineageRelation.SUPPLIES_EVALUATION,
    ) in edges
    assert len(projection.topology_revision) == 64
    assert len(projection.content_revision) == 64


def test_unknown_evaluation_version_is_never_attached_to_latest() -> None:
    service = LineageProjectionService(
        datasets_service=_Datasets([_dataset("ds_001", "Dataset A")]),
        training_service=_Training([_run("trn_001")]),
        model_versions_service=_Versions(
            [_version("mdl_latest", "trn_001")]
        ),
        experiments_service=_Experiments(
            [_experiment("evr_001", "mdl_missing")]
        ),
    )

    projection = service.build_projection()

    evaluation_id = lineage_node_id(
        LineageEntityKind.EVALUATION_RUN,
        "evr_001",
    )
    assert all(
        not (
            edge.target_node_id == evaluation_id
            and edge.relation is LineageRelation.EVALUATES_VERSION
        )
        for edge in projection.edges
    )
    unresolved = [
        item
        for item in projection.unresolved
        if item.dependent_node_id == evaluation_id
        and item.expected_kind is LineageEntityKind.MODEL_VERSION
    ]
    assert len(unresolved) == 1
    assert unresolved[0].reference == "mdl_missing"
    assert unresolved[0].reason_code == "unknown_reference"


def test_ambiguous_dataset_title_is_not_guessed() -> None:
    service = LineageProjectionService(
        datasets_service=_Datasets(
            [
                _dataset("ds_001", "Shared title"),
                _dataset("ds_002", "Shared title"),
            ]
        ),
        training_service=_Training(
            [_run("trn_001", dataset="Shared title")]
        ),
    )

    projection = service.build_projection()

    run_id = lineage_node_id(LineageEntityKind.TRAINING_RUN, "trn_001")
    assert all(
        not (
            edge.target_node_id == run_id
            and edge.relation is LineageRelation.USES_DATASET
        )
        for edge in projection.edges
    )
    unresolved = [
        item
        for item in projection.unresolved
        if item.dependent_node_id == run_id
        and item.expected_kind is LineageEntityKind.DATASET
    ]
    assert len(unresolved) == 1
    assert unresolved[0].reason_code == "ambiguous_reference"


def test_source_failure_keeps_a_partial_projection() -> None:
    service = LineageProjectionService(
        datasets_service=_Datasets(error=RuntimeError("database busy")),
        training_service=_Training([_run("trn_001")]),
    )

    projection = service.build_projection()

    run_id = lineage_node_id(LineageEntityKind.TRAINING_RUN, "trn_001")
    assert projection.node(run_id) is not None
    assert projection.source_failures == (
        next(
            item
            for item in projection.source_failures
            if item.source is LineageSource.DATASETS
        ),
    )
    assert projection.source_failures[0].error_type == "RuntimeError"
    assert any(
        item.dependent_node_id == run_id
        and item.expected_kind is LineageEntityKind.DATASET
        for item in projection.unresolved
    )


def test_content_change_does_not_force_a_topology_revision() -> None:
    training = _Training(
        [_run("trn_001", status=TrainingRunStatus.RUNNING)]
    )
    service = LineageProjectionService(
        datasets_service=_Datasets([_dataset("ds_001", "Dataset A")]),
        training_service=training,
    )

    running = service.build_projection()
    training.items = [
        _run("trn_001", status=TrainingRunStatus.COMPLETED)
    ]
    completed = service.build_projection()

    assert running.topology_revision == completed.topology_revision
    assert running.content_revision != completed.content_revision
    run_id = lineage_node_id(LineageEntityKind.TRAINING_RUN, "trn_001")
    assert running.node(run_id).state is LineageState.RUNNING
    assert completed.node(run_id).state is LineageState.READY


def test_large_projection_is_deterministic_and_deduplicated() -> None:
    count = 1_000
    datasets = _Datasets([_dataset("ds_001", "Dataset A")])
    runs = [_run(f"trn_{index:04d}") for index in range(count)]
    versions = [
        _version(f"mdl_{index:04d}", f"trn_{index:04d}")
        for index in range(count)
    ]
    experiments = [
        _experiment(
            f"evr_{index:04d}",
            f"mdl_{index:04d}",
            artifact=f"/artifacts/trn_{index:04d}",
        )
        for index in range(count)
    ]
    training = _Training(runs)
    model_versions = _Versions(versions)
    evaluation_runs = _Experiments(experiments)
    service = LineageProjectionService(
        datasets_service=datasets,
        training_service=training,
        model_versions_service=model_versions,
        experiments_service=evaluation_runs,
    )

    first = service.build_projection()
    training.items.reverse()
    model_versions.items.reverse()
    evaluation_runs.items.reverse()
    second = service.build_projection()

    assert first.topology_revision == second.topology_revision
    assert first.content_revision == second.content_revision
    assert len({node.node_id for node in first.nodes}) == len(first.nodes)
    assert len(first.edges) == len(set(first.edges))
    assert first.unresolved == ()
    assert len(
        [
            node
            for node in first.nodes
            if node.kind is LineageEntityKind.BASE_MODEL
        ]
    ) == 1
    assert len(
        [
            node
            for node in first.nodes
            if node.kind is LineageEntityKind.PERSONA_PROFILE
        ]
    ) == 1


def test_long_entity_ids_have_bounded_stable_node_ids() -> None:
    entity_id = "/very/long/" + "segment/" * 100

    first = lineage_node_id(LineageEntityKind.ARTIFACT, entity_id)
    second = lineage_node_id(LineageEntityKind.ARTIFACT, entity_id)

    assert first == second
    assert first.startswith("artifact:sha256-")
    assert len(first) < 100

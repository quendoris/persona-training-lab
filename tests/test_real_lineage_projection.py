from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.ui.agents.real_lineage import build_real_lineage
from persona_training_lab.ui.viewmodels.agents import AgentsViewModel


class _ListService:
    def __init__(self, method_name: str, values: list[object]) -> None:
        self._method_name = method_name
        self._values = values

    def __getattr__(self, name: str):
        if name != self._method_name:
            raise AttributeError(name)
        return lambda: list(self._values)


def _portrait(
    experiment_id: str,
    title: str,
    version_id: str,
    artifact: str,
) -> SimpleNamespace:
    subtitle = (
        "PORTRAIT: 1/1 Big Five items · snapshot · "
        f"model_version={version_id} · artifact={artifact} · "
        "battery=v1 · scoring=s1\n\n"
        "CASE 1\nTRAIT: Openness\nKEY: O1\nREVERSE: 0\n"
        "VALID_SCORE: 1\nRESPONSE: SCORE: 4"
    )
    return SimpleNamespace(
        experiment_id=experiment_id,
        title=title,
        subtitle=subtitle,
        status="Портрет собран",
    )


def test_projection_keeps_every_real_run_version_and_test() -> None:
    runs = [
        SimpleNamespace(
            run_id="trn_new",
            title="New run",
            status="Завершено",
            base_model="Qwen",
            profile="Мия",
            dataset_version="ds_v2",
            epoch_progress="3 / 3",
            loss="0.1",
            progress="1.0",
            artifact_path="/artifacts/new",
            error_message="",
        ),
        SimpleNamespace(
            run_id="trn_old",
            title="Old run",
            status="Завершено",
            base_model="Qwen",
            profile="Мия",
            dataset_version="ds_v1",
            epoch_progress="2 / 2",
            loss="0.2",
            progress="1.0",
            artifact_path="/artifacts/old",
            error_message="",
        ),
    ]
    versions = [
        SimpleNamespace(
            version_id="mdl_new",
            title="New weights",
            status="Готова",
            base_model="Qwen",
            profile_title="Мия",
            dataset_title="ds_v2",
            training_run_id="trn_new",
            artifact_path="/artifacts/new",
            quality_summary="ok",
        ),
        SimpleNamespace(
            version_id="mdl_old",
            title="Old weights",
            status="Готова",
            base_model="Qwen",
            profile_title="Мия",
            dataset_title="ds_v1",
            training_run_id="trn_old",
            artifact_path="/artifacts/old",
            quality_summary="ok",
        ),
    ]
    experiments = [
        _portrait("evr_new", "New portrait", "mdl_new", "/artifacts/new"),
        _portrait("evr_old", "Old portrait", "mdl_old", "/artifacts/old"),
    ]
    datasets = [
        SimpleNamespace(
            dataset_id="ds_2",
            title="ds_v2",
            status="Одобрен для обучения",
            record_count=10,
            valid_count=10,
            invalid_count=0,
        ),
        SimpleNamespace(
            dataset_id="ds_1",
            title="ds_v1",
            status="Одобрен для обучения",
            record_count=8,
            valid_count=8,
            invalid_count=0,
        ),
    ]
    vm = AgentsViewModel(
        training_service=_ListService("list_training_runs", runs),
        model_versions_service=_ListService("list_model_versions", versions),
        datasets_service=_ListService("list_datasets", datasets),
        experiments_service=_ListService("list_experiments", experiments),
    )

    projection = build_real_lineage(vm)
    by_id = {node.node_id: node for node in projection.nodes}

    assert "training" in by_id
    assert "snapshot" in by_id
    assert "portrait" in by_id
    assert by_id["training:trn_old"].parent_id.startswith("dataset:")
    assert by_id["version:mdl_old"].parent_id == "training:trn_old"
    assert by_id["portrait:evr_old"].parent_id == "version:mdl_old"
    assert projection.entity_context["version:mdl_old"]["artifact_path"] == "/artifacts/old"
    assert {
        (claim.resource_kind, claim.resource_id)
        for claim in projection.resources["portrait:evr_old"]
    } == {
        ("artifact_path", "/artifacts/old"),
        ("experiment", "evr_old"),
        ("model_version", "mdl_old"),
    }


def test_projection_signature_changes_when_runtime_status_changes() -> None:
    run = SimpleNamespace(
        run_id="trn_live",
        title="Live run",
        status="Выполняется",
        base_model="Qwen",
        profile="Мия",
        dataset_version="ds",
        epoch_progress="1 / 3",
        loss="0.8",
        progress="0.3",
        artifact_path="",
        error_message="",
    )
    service = _ListService("list_training_runs", [run])
    vm = AgentsViewModel(training_service=service)

    before = build_real_lineage(vm)
    run.status = "Завершено"
    run.progress = "1.0"
    run.artifact_path = "/artifacts/live"
    after = build_real_lineage(vm)

    assert before.signature != after.signature
    assert next(
        node for node in before.nodes if node.node_id == "training"
    ).tone == "pending"
    assert next(
        node for node in after.nodes if node.node_id == "training"
    ).tone == "good"

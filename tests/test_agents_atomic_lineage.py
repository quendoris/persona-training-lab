from __future__ import annotations

from dataclasses import replace

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageProjectionService,
)
from persona_training_lab.application.lineage.snapshot import (
    LineageDatasetRecord,
    LineageEvaluationRecord,
    LineageModelVersionRecord,
    LineageSourceSnapshot,
    LineageTrainingRunRecord,
)
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.agents.atomic_lineage import build_real_lineage
from persona_training_lab.ui.viewmodels.agents_lineage import AgentsViewModel


class _Reader:
    def __init__(self, snapshot: LineageSourceSnapshot) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def read_lineage_snapshot(self) -> LineageSourceSnapshot:
        self.calls += 1
        return self.snapshot


def _source() -> LineageSourceSnapshot:
    return LineageSourceSnapshot(
        datasets=(
            LineageDatasetRecord(
                "ds_new",
                "New dataset",
                "approved",
                "/datasets/new.jsonl",
                "jsonl",
                20,
                20,
                0,
                "2026-08-06T12:00:00+00:00",
            ),
            LineageDatasetRecord(
                "ds_old",
                "Old dataset",
                "approved",
                "/datasets/old.jsonl",
                "jsonl",
                10,
                10,
                0,
                "2026-08-06T10:00:00+00:00",
            ),
        ),
        training_runs=(
            LineageTrainingRunRecord(
                "trn_old",
                "Old run",
                "completed",
                "Qwen",
                "Mia",
                "ds_old",
                "full",
                "1.0",
                "2 / 2",
                "0.2",
                "/artifacts/old",
                "",
                "2026-08-06T10:01:00+00:00",
            ),
            LineageTrainingRunRecord(
                "trn_new",
                "New run",
                "completed",
                "Qwen",
                "Mia",
                "ds_new",
                "full",
                "1.0",
                "3 / 3",
                "0.1",
                "/artifacts/new",
                "",
                "2026-08-06T12:01:00+00:00",
            ),
        ),
        model_versions=(
            LineageModelVersionRecord(
                "mdl_old",
                "Old weights",
                "ready",
                "Qwen",
                "Mia",
                "Old dataset",
                "trn_old",
                "/artifacts/old",
                "ok",
                "2026-08-06T10:02:00+00:00",
            ),
            LineageModelVersionRecord(
                "mdl_new",
                "New weights",
                "ready",
                "Qwen",
                "Mia",
                "New dataset",
                "trn_new",
                "/artifacts/new",
                "ok",
                "2026-08-06T12:02:00+00:00",
            ),
        ),
        evaluations=(
            LineageEvaluationRecord(
                "evr_old",
                "Old portrait",
                "PORTRAIT: 1/1 · model_version=mdl_old · "
                "artifact=/artifacts/old",
                "completed",
                "2026-08-06T10:03:00+00:00",
            ),
            LineageEvaluationRecord(
                "evr_new",
                "New portrait",
                "PORTRAIT: 1/1 · model_version=mdl_new · "
                "artifact=/artifacts/new",
                "completed",
                "2026-08-06T12:03:00+00:00",
            ),
        ),
    )


def _view_model(
    source: LineageSourceSnapshot,
) -> tuple[AgentsViewModel, _Reader]:
    reader = _Reader(source)
    vm = AgentsViewModel(
        lineage_projection_service=AtomicLineageProjectionService(reader),
    )
    return vm, reader


def test_latest_aliases_are_selected_by_timestamp_not_input_order() -> None:
    vm, reader = _view_model(_source())

    projection = build_real_lineage(vm)
    by_id = {node.node_id: node for node in projection.nodes}

    assert reader.calls == 1
    assert (
        projection.entity_context["training"]["training_run_id"]
        == "trn_new"
    )
    assert (
        projection.entity_context["snapshot"]["model_version_id"]
        == "mdl_new"
    )
    assert (
        projection.entity_context["portrait"]["experiment_id"]
        == "evr_new"
    )
    assert projection.entity_context["dataset"]["dataset_id"] == "ds_new"
    assert "training_run:trn_old" in by_id
    assert "model_version:mdl_old" in by_id
    assert "evaluation_run:evr_old" in by_id
    assert by_id["portrait"].parent_id == "snapshot"
    claims = {
        (claim.resource_kind, claim.resource_id)
        for claim in projection.resources["snapshot"]
    }
    assert {
        ("artifact_path", "/artifacts/new"),
        ("dataset", "ds_new"),
        ("model_definition", "Qwen"),
        ("model_version", "mdl_new"),
        ("profile", "Mia"),
        ("training_run", "trn_new"),
    } <= claims


def test_alias_changes_have_their_own_presentation_revision() -> None:
    first = _source()
    old_version = replace(
        first.model_versions[0],
        updated_at="2026-08-06T13:00:00+00:00",
    )
    second = replace(
        first,
        model_versions=(old_version, first.model_versions[1]),
    )
    first_vm, _ = _view_model(first)
    second_vm, _ = _view_model(second)

    first_projection = build_real_lineage(first_vm)
    second_projection = build_real_lineage(second_vm)

    assert (
        first_vm.build_lineage_snapshot().projection.content_revision
        == second_vm.build_lineage_snapshot().projection.content_revision
    )
    assert first_projection.signature != second_projection.signature
    assert (
        first_projection.entity_context["snapshot"]["model_version_id"]
        == "mdl_new"
    )
    assert (
        second_projection.entity_context["snapshot"]["model_version_id"]
        == "mdl_old"
    )


def test_unresolved_evaluation_is_never_attached_to_latest_snapshot() -> None:
    source = _source()
    broken = LineageEvaluationRecord(
        "evr_broken",
        "Broken portrait",
        "PORTRAIT: 0/1 · model_version=mdl_missing",
        "partial",
        "2026-08-06T14:00:00+00:00",
    )
    source = replace(source, evaluations=(broken, *source.evaluations))
    vm, _ = _view_model(source)

    projection = build_real_lineage(vm)
    portrait = next(
        node for node in projection.nodes if node.node_id == "portrait"
    )

    assert portrait.parent_id is None
    assert (
        projection.entity_context["portrait"]["model_version_id"]
        == "mdl_missing"
    )
    detail_body = projection.details["portrait"].body
    assert isinstance(detail_body, UserMessage)
    assert detail_body.key == "agents.detail.semantic_body"
    assert "unknown_reference" in str(detail_body.values["unresolved"])


def test_empty_atomic_projection_keeps_explicit_presentation_placeholders() -> None:
    vm, reader = _view_model(LineageSourceSnapshot())

    projection = build_real_lineage(vm)
    by_id = {node.node_id: node for node in projection.nodes}

    assert reader.calls == 1
    assert {
        "base",
        "dataset",
        "training",
        "snapshot",
        "portrait",
        "delta",
    } <= set(by_id)
    subtitle = by_id["snapshot"].subtitle
    assert isinstance(subtitle, UserMessage)
    assert subtitle.key == "agents.node.placeholder.subtitle"
    assert projection.resources["snapshot"] == ()

from __future__ import annotations

from typing import cast

from persona_training_lab.application.experiments.service import (
    ExperimentSummary,
    ExperimentsService,
)
from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus
from persona_training_lab.ui.viewmodels.analysis_lineage import AnalysisViewModel
from persona_training_lab.ui.viewmodels.evaluation import EvaluationText


class _ExperimentsSource:
    def __init__(self, rows: list[ExperimentSummary]) -> None:
        self._rows = rows

    def list_experiments(self) -> list[ExperimentSummary]:
        return list(self._rows)


def _portrait_payload(
    *,
    model_version_id: str,
    first_score: int,
    reverse_score: int,
    battery: str = "big_five_short_v1",
    scoring: str = "big_five_score_v1",
) -> str:
    return (
        "PORTRAIT: 2/2 Big Five items · "
        f"snapshot={model_version_id} · "
        f"model_version={model_version_id} · "
        f"artifact=/models/{model_version_id} · "
        f"battery={battery} · scoring={scoring}\n\n"
        "CASE 1\n"
        "TRAIT: Extraversion\n"
        "KEY: E1\n"
        "REVERSE: 0\n"
        "ITEM: forward\n"
        "STATUS: responding\n"
        "VALID_SCORE: 1\n"
        f"RAW_RESPONSE: SCORE: {first_score}\n"
        f"RESPONSE: SCORE: {first_score}\n\n"
        "CASE 2\n"
        "TRAIT: Extraversion\n"
        "KEY: E2R\n"
        "REVERSE: 1\n"
        "ITEM: reverse\n"
        "STATUS: responding\n"
        "VALID_SCORE: 1\n"
        f"RAW_RESPONSE: SCORE: {reverse_score}\n"
        f"RESPONSE: SCORE: {reverse_score}"
    )


def _experiment(
    experiment_id: str,
    *,
    model_version_id: str,
    first_score: int,
    reverse_score: int,
    battery: str = "big_five_short_v1",
    scoring: str = "big_five_score_v1",
    updated_at: str,
) -> ExperimentSummary:
    return ExperimentSummary(
        experiment_id=experiment_id,
        title=f"portrait {experiment_id}",
        subtitle=_portrait_payload(
            model_version_id=model_version_id,
            first_score=first_score,
            reverse_score=reverse_score,
            battery=battery,
            scoring=scoring,
        ),
        status=EvaluationRunStatus.COMPLETED.value,
        status_code=EvaluationRunStatus.COMPLETED,
        updated_at=updated_at,
    )


def _view_model(
    latest: ExperimentSummary,
    previous: ExperimentSummary,
) -> AnalysisViewModel:
    source = _ExperimentsSource([latest, previous])
    return AnalysisViewModel(
        experiments_service=cast(ExperimentsService, source)
    )


def test_matching_protocol_versions_allow_factor_delta() -> None:
    previous = _experiment(
        "evr_old",
        model_version_id="mdl_old",
        first_score=2,
        reverse_score=4,
        updated_at="2026-08-18T10:00:00Z",
    )
    latest = _experiment(
        "evr_new",
        model_version_id="mdl_new",
        first_score=4,
        reverse_score=2,
        updated_at="2026-08-19T10:00:00Z",
    )

    vm = _view_model(latest, previous)

    assert "E=+2.00" in vm.metrics[1].delta
    assert vm.metric_note_model(vm.metrics[1]) == EvaluationText(
        "analysis.metric.note.delta.ready"
    )


def test_mismatched_protocol_versions_block_factor_delta() -> None:
    previous = _experiment(
        "evr_old",
        model_version_id="mdl_old",
        first_score=2,
        reverse_score=4,
        battery="big_five_short_v0",
        updated_at="2026-08-18T10:00:00Z",
    )
    latest = _experiment(
        "evr_new",
        model_version_id="mdl_new",
        first_score=4,
        reverse_score=2,
        updated_at="2026-08-19T10:00:00Z",
    )

    vm = _view_model(latest, previous)

    assert vm.metrics[1].delta == "—"
    assert vm.metric_note_model(vm.metrics[1]) == EvaluationText(
        "analysis.pair.same_protocol"
    )
    assert vm.delta_models() == (
        EvaluationText("analysis.pair.same_protocol"),
    )


def test_unknown_protocol_metadata_is_not_treated_as_comparable() -> None:
    previous = _experiment(
        "evr_old",
        model_version_id="mdl_old",
        first_score=2,
        reverse_score=4,
        battery="",
        scoring="",
        updated_at="2026-08-18T10:00:00Z",
    )
    latest = _experiment(
        "evr_new",
        model_version_id="mdl_new",
        first_score=4,
        reverse_score=2,
        updated_at="2026-08-19T10:00:00Z",
    )

    vm = _view_model(latest, previous)

    assert vm.metrics[1].delta == "—"
    assert vm.metric_note_model(vm.metrics[1]) == EvaluationText(
        "analysis.pair.same_protocol"
    )


def test_lineage_pair_reports_protocol_mismatch_without_substitution() -> None:
    previous = _experiment(
        "evr_old",
        model_version_id="mdl_old",
        first_score=2,
        reverse_score=4,
        scoring="big_five_score_v0",
        updated_at="2026-08-18T10:00:00Z",
    )
    latest = _experiment(
        "evr_new",
        model_version_id="mdl_new",
        first_score=4,
        reverse_score=2,
        updated_at="2026-08-19T10:00:00Z",
    )
    vm = _view_model(latest, previous)

    vm.set_lineage_context(
        {
            "selected": {"model_version_id": "mdl_old"},
            "current": {"model_version_id": "mdl_new"},
        }
    )

    subtitle = vm.header_subtitle_model()
    assert isinstance(subtitle, EvaluationText)
    assert subtitle.key == "analysis.header.subtitle.pair_missing"
    reason = subtitle.values["reason"]
    assert reason == EvaluationText("analysis.pair.same_protocol")
    assert vm.metrics[1].delta == "—"

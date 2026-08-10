from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.analysis.service import AnalysisService
from persona_training_lab.application.experiments.portrait import (
    PortraitRunRecord,
    parse_portrait_payload,
)
from persona_training_lab.application.experiments.service import (
    ExperimentSummary,
    ExperimentsService,
)
from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)
from persona_training_lab.ui.viewmodels.evaluation import (
    EvaluationText,
    evaluation_status_text,
    evaluation_text,
    render_base_evaluation_text,
)


TRAIT_ORDER = (
    "Extraversion",
    "Agreeableness",
    "Conscientiousness",
    "Emotional Stability",
    "Openness",
)
TRAIT_LABELS = {
    "Extraversion": "E",
    "Agreeableness": "A",
    "Conscientiousness": "C",
    "Emotional Stability": "S",
    "Openness": "O",
}

EvaluationTextValue = str | EvaluationText


@dataclass(slots=True, frozen=True)
class CompareMetric:
    title: str
    delta: str
    note: str
    title_model: EvaluationTextValue | None = None
    note_model: EvaluationTextValue | None = None


@dataclass(slots=True, frozen=True)
class CompareSummary:
    title: str
    subtitle: str
    profile_match: str
    stability: str
    contradiction: str
    title_model: EvaluationTextValue | None = None
    subtitle_model: EvaluationTextValue | None = None
    stability_model: EvaluationTextValue | None = None
    contradiction_model: EvaluationTextValue | None = None


@dataclass(slots=True, frozen=True)
class CompareSample:
    title: str
    left_note: str
    right_note: str
    title_model: EvaluationTextValue | None = None
    left_models: tuple[EvaluationTextValue, ...] = ()
    right_models: tuple[EvaluationTextValue, ...] = ()


def _compat_text(value: EvaluationTextValue) -> str:
    return render_base_evaluation_text(value)


def _compare_metric(
    title: EvaluationTextValue,
    delta: str,
    note: EvaluationTextValue,
) -> CompareMetric:
    return CompareMetric(
        title=_compat_text(title),
        delta=delta,
        note=_compat_text(note),
        title_model=title,
        note_model=note,
    )


def _compare_summary(
    title: EvaluationTextValue,
    subtitle: EvaluationTextValue,
    profile_match: str,
    stability: EvaluationTextValue,
    contradiction: EvaluationTextValue,
) -> CompareSummary:
    return CompareSummary(
        title=_compat_text(title),
        subtitle=_compat_text(subtitle),
        profile_match=profile_match,
        stability=_compat_text(stability),
        contradiction=_compat_text(contradiction),
        title_model=title,
        subtitle_model=subtitle,
        stability_model=stability,
        contradiction_model=contradiction,
    )


def _compare_sample(
    title: EvaluationTextValue,
    left_models: tuple[EvaluationTextValue, ...],
    right_models: tuple[EvaluationTextValue, ...],
) -> CompareSample:
    return CompareSample(
        title=_compat_text(title),
        left_note="\n".join(_compat_text(item) for item in left_models),
        right_note="\n".join(_compat_text(item) for item in right_models),
        title_model=title,
        left_models=left_models,
        right_models=right_models,
    )


def _method_summary() -> CompareSummary:
    return _compare_summary(
        evaluation_text("analysis.summary.method"),
        evaluation_text("analysis.summary.method.subtitle"),
        "1-5",
        evaluation_text("analysis.summary.method.stability"),
        evaluation_text("analysis.value.manual"),
    )


def _waiting_summary() -> CompareSummary:
    return _compare_summary(
        evaluation_text("analysis.summary.latest"),
        evaluation_text("analysis.value.waiting"),
        "—",
        evaluation_text("analysis.value.unavailable"),
        "—",
    )


@dataclass(slots=True, frozen=True)
class PortraitStats:
    title: str
    raw_status: str
    status_code: EvaluationRunStatus
    record: PortraitRunRecord
    failures: int
    scores: dict[str, float]
    samples: tuple[CompareSample, ...]

    @property
    def passed(self) -> int:
        return self.record.passed

    @property
    def total(self) -> int:
        return self.record.total


@dataclass(slots=True)
class AnalysisViewModel:
    analysis_service: AnalysisService | None = None
    experiments_service: ExperimentsService | None = None
    title: str = ""
    subtitle: str = ""
    left: CompareSummary = field(default_factory=_method_summary)
    right: CompareSummary = field(default_factory=_waiting_summary)
    metrics: tuple[CompareMetric, ...] = ()
    insights: tuple[str, ...] = ()
    deltas: tuple[str, ...] = ()
    samples: tuple[CompareSample, ...] = ()
    selected_model_version_id: str = ""
    current_model_version_id: str = ""
    selected_node_id: str = ""
    current_node_id: str = ""
    _title_model: EvaluationTextValue = field(
        default_factory=lambda: evaluation_text("analysis.header.title")
    )
    _subtitle_model: EvaluationTextValue = field(
        default_factory=lambda: evaluation_text(
            "analysis.header.subtitle.empty"
        )
    )
    _insight_models: tuple[EvaluationTextValue, ...] = ()
    _delta_models: tuple[EvaluationTextValue, ...] = ()

    def __post_init__(self) -> None:
        self.refresh()

    def set_lineage_context(self, payload: dict[str, object]) -> None:
        selected_raw = payload.get("selected", payload)
        current_raw = payload.get("current", {})
        selected = selected_raw if isinstance(selected_raw, dict) else {}
        current = current_raw if isinstance(current_raw, dict) else {}
        self.selected_model_version_id = str(
            selected.get("model_version_id", "") or ""
        )
        self.current_model_version_id = str(
            current.get("model_version_id", "") or ""
        )
        self.selected_node_id = str(
            selected.get("node_id", "") or ""
        )
        self.current_node_id = str(
            current.get("node_id", "") or ""
        )
        self.refresh()

    def refresh(self) -> None:
        if (
            self.selected_model_version_id
            and self.current_model_version_id
        ):
            self._refresh_lineage_pair()
            return
        if self.experiments_service is None:
            self._apply_analysis_connector()
            return
        try:
            experiments = self.experiments_service.list_experiments()
        except Exception:
            self._set_load_failed()
            return
        if not experiments:
            self._set_empty()
            return
        previous = experiments[1] if len(experiments) > 1 else None
        self._apply_experiment(experiments[0], previous)

    def _refresh_lineage_pair(self) -> None:
        selected_id = self.selected_model_version_id
        current_id = self.current_model_version_id
        service = self.experiments_service
        if service is None:
            self._set_missing_pair(
                selected_id,
                current_id,
                "service_unavailable",
            )
            return
        try:
            experiments = service.list_experiments()
        except Exception:
            self._set_missing_pair(
                selected_id,
                current_id,
                "load_failed",
            )
            return
        selected_experiment = self._experiment_for_version(
            experiments,
            selected_id,
        )
        current_experiment = self._experiment_for_version(
            experiments,
            current_id,
        )
        missing = tuple(
            dict.fromkeys(
                version_id
                for version_id, experiment in (
                    (selected_id, selected_experiment),
                    (current_id, current_experiment),
                )
                if experiment is None
            )
        )
        if missing:
            self._set_missing_pair(
                selected_id,
                current_id,
                "portrait_missing",
                missing=", ".join(missing),
            )
            return
        assert selected_experiment is not None
        assert current_experiment is not None
        self._apply_experiment(current_experiment, selected_experiment)
        self._title_model = evaluation_text(
            "analysis.header.title.pair",
            selected_id=selected_id,
            current_id=current_id,
        )
        self._subtitle_model = evaluation_text(
            "analysis.header.subtitle.pair",
            selected_id=selected_id,
            current_id=current_id,
        )
        self.title = render_base_evaluation_text(self._title_model)
        self.subtitle = render_base_evaluation_text(self._subtitle_model)

    @staticmethod
    def _experiment_for_version(
        experiments,
        version_id: str,
    ) -> ExperimentSummary | None:
        return next(
            (
                experiment
                for experiment in experiments
                if parse_portrait_payload(
                    experiment.subtitle
                ).model_version_id
                == version_id
            ),
            None,
        )

    def _apply_experiment(
        self,
        latest: ExperimentSummary,
        previous: ExperimentSummary | None = None,
    ) -> None:
        latest_stats = self._stats_from_experiment(latest)
        previous_stats = (
            self._stats_from_experiment(previous)
            if previous is not None
            else None
        )
        profile_type = self._profile_type(latest_stats.scores)
        score_line = self._score_line(latest_stats.scores)
        delta_line = (
            self._delta_line(
                previous_stats.scores,
                latest_stats.scores,
            )
            if previous_stats is not None
            else "—"
        )

        self._title_model = evaluation_text(
            "analysis.header.title.run",
            title=latest_stats.title,
        )
        self._subtitle_model = self._summary_model(latest_stats.record)
        self.title = render_base_evaluation_text(self._title_model)
        self.subtitle = render_base_evaluation_text(self._subtitle_model)
        if previous_stats is not None:
            self.left = _compare_summary(
                evaluation_text("analysis.summary.previous"),
                previous_stats.title,
                self._score_line(previous_stats.scores) or "—",
                evaluation_status_text(
                    previous_stats.status_code,
                    previous_stats.raw_status,
                ),
                str(previous_stats.failures),
            )
        else:
            self.left = _method_summary()
        self.right = _compare_summary(
            evaluation_text("analysis.summary.latest"),
            latest_stats.title,
            (
                f"{latest_stats.passed}/{latest_stats.total}"
                if latest_stats.total
                else "—"
            ),
            evaluation_status_text(
                latest_stats.status_code,
                latest_stats.raw_status,
            ),
            str(latest_stats.failures),
        )
        self.metrics = (
            _compare_metric(
                evaluation_text("analysis.metric.kpi"),
                score_line or "—",
                evaluation_text("analysis.metric.note.kpi"),
            ),
            _compare_metric(
                evaluation_text("analysis.metric.delta"),
                delta_line,
                evaluation_text(
                    "analysis.metric.note.delta.ready"
                    if previous_stats is not None
                    else "analysis.metric.note.delta.missing"
                ),
            ),
            _compare_metric(
                evaluation_text("analysis.metric.errors"),
                str(latest_stats.failures),
                evaluation_text("analysis.metric.note.errors"),
            ),
        )
        self._insight_models = self._build_insight_models(
            latest_stats,
            previous_stats,
            profile_type,
        )
        self.insights = tuple(
            self._legacy_text(item) for item in self._insight_models
        )
        self._delta_models = self._build_delta_models(
            latest_stats,
            previous_stats,
        )
        self.deltas = tuple(
            self._legacy_text(item) for item in self._delta_models
        )
        self.samples = self._compare_samples(
            latest_stats,
            previous_stats,
        )

    @staticmethod
    def _stats_from_experiment(
        experiment: ExperimentSummary | None,
    ) -> PortraitStats:
        if experiment is None:
            return PortraitStats(
                title="—",
                raw_status="—",
                status_code=EvaluationRunStatus.UNKNOWN,
                record=PortraitRunRecord("—", 0, 0, (), cases=()),
                failures=0,
                scores={},
                samples=(),
            )
        record = parse_portrait_payload(experiment.subtitle)
        failures = max(
            record.invalid_count,
            max(0, record.total - record.passed),
        )
        if experiment.status_code in {
            EvaluationRunStatus.PARTIAL,
            EvaluationRunStatus.FAILED,
        }:
            failures = max(1, failures)
        return PortraitStats(
            title=experiment.title,
            raw_status=experiment.status,
            status_code=experiment.status_code,
            record=record,
            failures=failures,
            scores=record.trait_scores(),
            samples=tuple(
                AnalysisViewModel._sample_from_case(case)
                for case in record.cases
            ),
        )

    @staticmethod
    def _sample_from_case(case) -> CompareSample:
        left_models: list[EvaluationTextValue] = []
        right_models: list[EvaluationTextValue] = []
        if case.trait:
            left_models.append(
                evaluation_text(
                    "analysis.sample.field.trait",
                    value=case.trait,
                )
            )
        if case.key:
            left_models.append(
                evaluation_text(
                    "analysis.sample.field.key",
                    value=case.key,
                )
            )
        if case.item:
            left_models.append(
                evaluation_text(
                    "analysis.sample.field.item",
                    value=case.item,
                )
            )
        right_models.extend(
            (
                evaluation_text(
                    "analysis.sample.field.status",
                    status=evaluation_text(
                        f"tests.model_status.{case.status_code.value}"
                    ),
                ),
                evaluation_text(
                    "analysis.sample.field.raw_score",
                    value=case.score if case.score is not None else "—",
                ),
                evaluation_text(
                    "analysis.sample.field.score",
                    value=(
                        case.adjusted_score
                        if case.adjusted_score is not None
                        else "—"
                    ),
                ),
            )
        )
        if case.response:
            right_models.append(
                evaluation_text(
                    "analysis.sample.field.response",
                    value=case.response,
                )
            )
        if case.raw_response and case.raw_response != case.response:
            right_models.append(
                evaluation_text(
                    "analysis.sample.field.raw_response",
                    value=case.raw_response,
                )
            )
        return _compare_sample(
            evaluation_text(
                "analysis.sample.title",
                index=case.index,
            ),
            tuple(left_models),
            tuple(right_models),
        )

    @staticmethod
    def _score_line(scores: dict[str, float]) -> str:
        return " · ".join(
            f"{TRAIT_LABELS[key]}={scores[key]:.2f}"
            for key in TRAIT_ORDER
            if key in scores
        )

    @staticmethod
    def _delta_line(
        previous: dict[str, float],
        latest: dict[str, float],
    ) -> str:
        parts: list[str] = []
        for key in TRAIT_ORDER:
            if key not in previous or key not in latest:
                continue
            parts.append(
                f"{TRAIT_LABELS[key]}={latest[key] - previous[key]:+.2f}"
            )
        return " · ".join(parts) if parts else "—"

    @staticmethod
    def _profile_type(scores: dict[str, float]) -> str:
        if not scores:
            return ""
        top = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:2]
        return " + ".join(name for name, _value in top)

    def _build_insight_models(
        self,
        latest: PortraitStats,
        previous: PortraitStats | None,
        profile_type: str,
    ) -> tuple[EvaluationTextValue, ...]:
        if not latest.scores:
            return (
                evaluation_text("analysis.insight.no_scores.detect"),
                evaluation_text("analysis.insight.no_scores.format"),
                evaluation_text("analysis.insight.no_scores.limit"),
            )
        strongest = max(
            latest.scores.items(),
            key=lambda item: item[1],
        )
        status_model = evaluation_status_text(
            latest.status_code,
            latest.raw_status,
        )
        if previous is None or not previous.scores:
            return (
                evaluation_text(
                    "analysis.insight.portrait",
                    passed=latest.passed,
                    total=latest.total,
                    status=status_model,
                ),
                evaluation_text(
                    "analysis.insight.profile_type",
                    profile_type=profile_type,
                ),
                evaluation_text("analysis.insight.need_second"),
            )
        biggest_trait, biggest_delta = self._largest_abs_delta(
            previous.scores,
            latest.scores,
        )
        return (
            evaluation_text(
                "analysis.insight.portrait",
                passed=latest.passed,
                total=latest.total,
                status=status_model,
            ),
            evaluation_text(
                "analysis.insight.strongest",
                trait=strongest[0],
                value=f"{strongest[1]:.2f}",
            ),
            evaluation_text(
                "analysis.insight.biggest_delta",
                trait=biggest_trait,
                delta=f"{biggest_delta:+.2f}",
            ),
        )

    @staticmethod
    def _build_delta_models(
        latest: PortraitStats,
        previous: PortraitStats | None,
    ) -> tuple[EvaluationTextValue, ...]:
        if previous is None or not previous.scores or not latest.scores:
            return (
                evaluation_text("analysis.delta.need_two"),
                evaluation_text("analysis.delta.run_again"),
                evaluation_text("analysis.delta.auto_compare"),
            )
        rows = tuple(
            evaluation_text(
                "analysis.delta.value",
                trait=trait,
                previous=f"{previous.scores[trait]:.2f}",
                latest=f"{latest.scores[trait]:.2f}",
                delta=f"{latest.scores[trait] - previous.scores[trait]:+.2f}",
            )
            for trait in TRAIT_ORDER
            if trait in previous.scores and trait in latest.scores
        )
        return rows or (evaluation_text("analysis.delta.no_common"),)

    @staticmethod
    def _compare_samples(
        latest: PortraitStats,
        previous: PortraitStats | None,
    ) -> tuple[CompareSample, ...]:
        if previous is None or not previous.samples:
            if latest.samples:
                return latest.samples
            right_models: tuple[EvaluationTextValue, ...] = (
                (latest.record.raw_summary,)
                if latest.record.raw_summary
                else (evaluation_text("analysis.sample.empty.note"),)
            )
            return (
                _compare_sample(
                    evaluation_text("analysis.sample.empty.title"),
                    (evaluation_text("analysis.value.unavailable"),),
                    right_models,
                ),
            )
        compared: list[CompareSample] = []
        for index, sample in enumerate(latest.samples[:10]):
            if index < len(previous.samples):
                left_sample = previous.samples[index]
                left_models = left_sample.right_models or (
                    left_sample.right_note,
                )
            else:
                left_models = (
                    evaluation_text("analysis.sample.previous_missing"),
                )
            compared.append(
                _compare_sample(
                    sample.title_model or sample.title,
                    tuple(left_models),
                    sample.right_models or (sample.right_note,),
                )
            )
        return tuple(compared)

    @staticmethod
    def _largest_abs_delta(
        previous: dict[str, float],
        latest: dict[str, float],
    ) -> tuple[str, float]:
        common = [
            (trait, latest[trait] - previous[trait])
            for trait in TRAIT_ORDER
            if trait in previous and trait in latest
        ]
        if not common:
            return "—", 0.0
        return max(common, key=lambda item: abs(item[1]))

    def _set_empty(self) -> None:
        self._title_model = evaluation_text("analysis.header.title")
        self._subtitle_model = evaluation_text(
            "analysis.header.subtitle.empty"
        )
        self.title = render_base_evaluation_text(self._title_model)
        self.subtitle = render_base_evaluation_text(self._subtitle_model)
        self.left = _method_summary()
        self.right = _waiting_summary()
        self.metrics = self._empty_metrics()
        self._insight_models = (
            evaluation_text("analysis.insight.empty"),
        )
        self.insights = tuple(
            self._legacy_text(item) for item in self._insight_models
        )
        self._delta_models = (
            evaluation_text("analysis.delta.need_two"),
        )
        self.deltas = tuple(
            self._legacy_text(item) for item in self._delta_models
        )
        self.samples = (
            _compare_sample(
                evaluation_text("analysis.sample.empty.title"),
                (evaluation_text("analysis.value.unavailable"),),
                (evaluation_text("analysis.sample.empty.note"),),
            ),
        )

    def _set_load_failed(self) -> None:
        self._set_empty()
        self._subtitle_model = evaluation_text(
            "analysis.header.subtitle.load_failed"
        )
        self.subtitle = render_base_evaluation_text(self._subtitle_model)
        self._insight_models = (
            evaluation_text("analysis.insight.load_failed"),
        )
        self.insights = tuple(
            self._legacy_text(item) for item in self._insight_models
        )

    def _set_missing_pair(
        self,
        selected_id: str,
        current_id: str,
        reason_code: str,
        **values: object,
    ) -> None:
        self._title_model = evaluation_text(
            "analysis.header.title.pair",
            selected_id=selected_id,
            current_id=current_id,
        )
        reason = evaluation_text(
            f"analysis.pair.reason.{reason_code}",
            **values,
        )
        self._subtitle_model = evaluation_text(
            "analysis.header.subtitle.pair_missing",
            reason=reason,
        )
        self.title = render_base_evaluation_text(self._title_model)
        self.subtitle = render_base_evaluation_text(self._subtitle_model)
        self.left = _compare_summary(
            evaluation_text("analysis.summary.selected"),
            selected_id,
            "—",
            evaluation_text("analysis.value.portrait_missing"),
            "—",
        )
        self.right = _compare_summary(
            evaluation_text("analysis.summary.current"),
            current_id,
            "—",
            evaluation_text("analysis.value.portrait_missing"),
            "—",
        )
        self.metrics = (
            _compare_metric(
                evaluation_text("analysis.metric.kpi"),
                "—",
                evaluation_text("analysis.metric.note.pair_required"),
            ),
            _compare_metric(
                evaluation_text("analysis.metric.delta"),
                "—",
                evaluation_text("analysis.metric.note.pair_incomplete"),
            ),
            _compare_metric(
                evaluation_text("analysis.metric.errors"),
                "—",
                reason,
            ),
        )
        self._insight_models = (
            evaluation_text("analysis.pair.run_each"),
            evaluation_text("analysis.pair.same_protocol"),
            evaluation_text("analysis.pair.auto_select"),
        )
        self.insights = tuple(
            self._legacy_text(item) for item in self._insight_models
        )
        self._delta_models = (
            evaluation_text("analysis.pair.no_substitution"),
        )
        self.deltas = tuple(
            self._legacy_text(item) for item in self._delta_models
        )
        self.samples = (
            _compare_sample(
                evaluation_text("analysis.sample.pair_waiting"),
                (selected_id,),
                (current_id,),
            ),
        )

    @staticmethod
    def _empty_metrics() -> tuple[CompareMetric, ...]:
        return (
            _compare_metric(
                evaluation_text("analysis.metric.kpi"),
                "—",
                evaluation_text("analysis.metric.note.empty"),
            ),
            _compare_metric(
                evaluation_text("analysis.metric.delta"),
                "—",
                evaluation_text("analysis.metric.note.delta.missing"),
            ),
            _compare_metric(
                evaluation_text("analysis.metric.errors"),
                "—",
                evaluation_text("analysis.metric.note.empty"),
            ),
        )

    @staticmethod
    def _summary_model(
        record: PortraitRunRecord,
    ) -> EvaluationTextValue:
        if record.total:
            return evaluation_text(
                "analysis.header.subtitle.summary",
                passed=record.passed,
                total=record.total,
                model_version=record.model_version_id or "—",
            )
        return record.raw_summary

    def _apply_analysis_connector(self) -> None:
        if self.analysis_service is None:
            self._set_empty()
            return
        try:
            results = self.analysis_service.list_analysis_results()
        except Exception:
            self._set_load_failed()
            return
        if not results:
            self._set_empty()
            return
        result = results[0]
        self._set_empty()
        self._title_model = evaluation_text(
            "analysis.header.title.result",
            result_id=result.result_id,
        )
        self._subtitle_model = result.subtitle
        self.title = render_base_evaluation_text(self._title_model)
        self.subtitle = render_base_evaluation_text(self._subtitle_model)

    def header_title_model(self) -> EvaluationTextValue:
        return self._title_model

    def header_subtitle_model(self) -> EvaluationTextValue:
        return self._subtitle_model

    @staticmethod
    def summary_title_model(
        summary: CompareSummary,
    ) -> EvaluationTextValue:
        return summary.title_model or summary.title

    @staticmethod
    def summary_subtitle_model(
        summary: CompareSummary,
    ) -> EvaluationTextValue:
        return summary.subtitle_model or summary.subtitle

    @staticmethod
    def summary_stability_model(
        summary: CompareSummary,
    ) -> EvaluationTextValue:
        return summary.stability_model or summary.stability

    @staticmethod
    def summary_contradiction_model(
        summary: CompareSummary,
    ) -> EvaluationTextValue:
        return summary.contradiction_model or summary.contradiction

    @staticmethod
    def metric_title_model(
        metric: CompareMetric,
    ) -> EvaluationTextValue:
        return metric.title_model or metric.title

    @staticmethod
    def metric_note_model(
        metric: CompareMetric,
    ) -> EvaluationTextValue:
        return metric.note_model or metric.note

    def insight_models(self) -> tuple[EvaluationTextValue, ...]:
        return self._insight_models

    def delta_models(self) -> tuple[EvaluationTextValue, ...]:
        return self._delta_models

    @staticmethod
    def sample_title_model(
        sample: CompareSample,
    ) -> EvaluationTextValue:
        return sample.title_model or sample.title

    @staticmethod
    def sample_left_models(
        sample: CompareSample,
    ) -> tuple[EvaluationTextValue, ...]:
        return sample.left_models or (sample.left_note,)

    @staticmethod
    def sample_right_models(
        sample: CompareSample,
    ) -> tuple[EvaluationTextValue, ...]:
        return sample.right_models or (sample.right_note,)

    @staticmethod
    def _legacy_text(value: EvaluationTextValue) -> str:
        return render_base_evaluation_text(value)

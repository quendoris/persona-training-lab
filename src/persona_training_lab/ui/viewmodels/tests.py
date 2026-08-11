from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.experiments.portrait import (
    PortraitCaseRecord,
    PortraitRunRecord,
    parse_portrait_payload,
)
from persona_training_lab.application.experiments.service import (
    ExperimentRunResult,
    ExperimentsService,
    experiment_result,
)
from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
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
from persona_training_lab.ui.viewmodels.experiment_semantics import (
    experiment_title_text,
)


EvaluationTextValue = str | EvaluationText
_RESULT_MESSAGE_KEYS = {
    "local_model_unavailable": "tests.message.local_model_unavailable",
    "model_version_not_found": "tests.message.model_version_not_found",
    "selected_weights_unavailable": "tests.message.selected_weights_unavailable",
    "model_unavailable": "tests.message.model_unavailable",
    "battery_load_failed": "tests.message.battery_load_failed",
    "resource_busy": "tests.message.resource_busy",
    "safe_stop": "tests.message.safe_stop",
    "storage_read_only": "tests.message.storage_read_only",
    "portrait_completed": "tests.message.portrait_completed",
    "portrait_partial": "tests.message.portrait_partial",
    "service_unavailable": "tests.message.service_unavailable",
}
_EMPTY_METRIC_NOTE_KEYS = {
    "empty": (
        "tests.metric.note.empty.runs",
        "tests.metric.note.empty.status",
        "tests.metric.note.empty.items",
        "tests.metric.note.empty.errors",
    ),
    "service_unavailable": (
        "tests.metric.note.service_unavailable.runs",
        "tests.metric.note.service_unavailable.status",
        "tests.metric.note.service_unavailable.items",
        "tests.metric.note.service_unavailable.errors",
    ),
    "load_failed": (
        "tests.metric.note.load_failed.runs",
        "tests.metric.note.load_failed.status",
        "tests.metric.note.load_failed.items",
        "tests.metric.note.load_failed.errors",
    ),
    "target_empty": (
        "tests.metric.note.target_empty.runs",
        "tests.metric.note.target_empty.status",
        "tests.metric.note.target_empty.items",
        "tests.metric.note.target_empty.errors",
    ),
}
_MODEL_STATUS_KEYS = {
    LocalModelStatus.UNCHECKED: "tests.model_status.unchecked",
    LocalModelStatus.CHECKING: "tests.model_status.checking",
    LocalModelStatus.FOUND: "tests.model_status.found",
    LocalModelStatus.MISSING: "tests.model_status.missing",
    LocalModelStatus.CHECK_FAILED: "tests.model_status.check_failed",
    LocalModelStatus.NOT_LOADED: "tests.model_status.not_loaded",
    LocalModelStatus.RESPONDING: "tests.model_status.responding",
    LocalModelStatus.INFERENCE_UNAVAILABLE: "tests.model_status.inference_unavailable",
    LocalModelStatus.GENERATING: "tests.model_status.generating",
    LocalModelStatus.GENERATION_FAILED: "tests.model_status.generation_failed",
    LocalModelStatus.UNKNOWN: "tests.model_status.unknown",
}


@dataclass(slots=True, frozen=True)
class EvaluationMetric:
    title: str
    value: str
    note: str
    title_model: EvaluationTextValue | None = None
    note_model: EvaluationTextValue | None = None


@dataclass(slots=True, frozen=True)
class EvaluationCase:
    title: str
    note: str
    title_model: EvaluationTextValue | None = None
    note_models: tuple[EvaluationTextValue, ...] = ()


def _compat_text(value: EvaluationTextValue) -> str:
    return render_base_evaluation_text(value)


def _evaluation_metric(
    title: EvaluationTextValue,
    value: str,
    note: EvaluationTextValue,
) -> EvaluationMetric:
    return EvaluationMetric(
        title=_compat_text(title),
        value=value,
        note=_compat_text(note),
        title_model=title,
        note_model=note,
    )


def _evaluation_case(
    title: EvaluationTextValue,
    note_models: tuple[EvaluationTextValue, ...],
) -> EvaluationCase:
    return EvaluationCase(
        title=_compat_text(title),
        note="\n".join(_compat_text(item) for item in note_models),
        title_model=title,
        note_models=note_models,
    )


@dataclass(slots=True)
class TestsViewModel:
    __test__ = False

    experiments_service: ExperimentsService | None = None
    title: str = ""
    subtitle: str = ""
    setup_rows: tuple[tuple[str, str], ...] = ()
    metrics: tuple[EvaluationMetric, ...] = ()
    problematic_cases: tuple[EvaluationCase, ...] = ()
    context_rows: tuple[str, ...] = ()
    run_in_progress: bool = False
    target_node_id: str = ""
    target_model_version_id: str = ""
    target_artifact_path: str = ""
    _title_model: EvaluationTextValue = field(
        default_factory=lambda: evaluation_text("tests.header.title")
    )
    _subtitle_model: EvaluationTextValue = field(
        default_factory=lambda: evaluation_text("tests.header.subtitle.empty")
    )
    _setup_models: tuple[
        tuple[EvaluationText, EvaluationTextValue], ...
    ] = ()
    _context_models: tuple[EvaluationTextValue, ...] = ()
    _run_message_model: EvaluationTextValue | None = None

    def __post_init__(self) -> None:
        self.refresh()

    def set_lineage_context(self, context: dict[str, str]) -> None:
        self.target_node_id = context.get("node_id", "")
        self.target_model_version_id = context.get(
            "model_version_id",
            "",
        )
        self.target_artifact_path = context.get("artifact_path", "")
        self.refresh()

    def refresh(self) -> None:
        self._apply_tests_connector()
        self._apply_target_setup()

    def _sync_header_compat(self) -> None:
        self.title = _compat_text(self._title_model)
        self.subtitle = _compat_text(self._subtitle_model)

    def _set_context_models(
        self,
        models: tuple[EvaluationTextValue, ...],
    ) -> None:
        self._context_models = models
        self.context_rows = tuple(_compat_text(item) for item in models)

    def _sync_setup_compat(self) -> None:
        self.setup_rows = tuple(
            (_compat_text(label), _compat_text(value))
            for label, value in self._setup_models
        )

    def _apply_tests_connector(self) -> None:
        if self.experiments_service is None:
            self._set_service_unavailable()
            return
        try:
            scenarios = self.experiments_service.list_experiments()
        except Exception:
            self._set_load_failed()
            return

        matching = self._matching_scenarios(scenarios)
        if self.target_model_version_id and not matching:
            self._set_target_empty()
            return
        if not matching:
            self._set_empty()
            return

        latest = matching[0]
        portrait = parse_portrait_payload(latest.subtitle)
        failures = self._failure_count(
            portrait,
            latest.status_code,
        )
        self._title_model = evaluation_text(
            "tests.header.title.run",
            title=experiment_title_text(latest),
        )
        self._subtitle_model = self._summary_model(portrait)
        self._sync_header_compat()
        self.metrics = (
            _evaluation_metric(
                evaluation_text(
                    "tests.metric.version_runs"
                    if self.target_model_version_id
                    else "tests.metric.runs"
                ),
                str(len(matching)),
                evaluation_text(
                    "tests.metric.note.version_runs",
                    version_id=self.target_model_version_id,
                )
                if self.target_model_version_id
                else evaluation_text("tests.metric.note.runs"),
            ),
            _evaluation_metric(
                evaluation_text("tests.metric.latest_status"),
                latest.status,
                evaluation_text("tests.metric.note.latest_status"),
            ),
            _evaluation_metric(
                evaluation_text("tests.metric.items"),
                self._answers_value(portrait),
                evaluation_text("tests.metric.note.items"),
            ),
            _evaluation_metric(
                evaluation_text("tests.metric.errors"),
                str(failures),
                evaluation_text("tests.metric.note.errors"),
            ),
        )
        self.problematic_cases = self._case_views(portrait) or (
            _evaluation_case(
                evaluation_text("tests.case.missing.title"),
                (evaluation_text("tests.case.missing.note"),),
            ),
        )
        self._set_context_models(
            (
                evaluation_text(
                    "tests.context.latest",
                    experiment_id=latest.experiment_id,
                ),
                evaluation_text(
                    "tests.context.status",
                    status=evaluation_status_text(
                        latest.status_code,
                        latest.status,
                    ),
                ),
                evaluation_text("tests.context.big_five"),
                evaluation_text("tests.context.kpi"),
            )
        )

    def _matching_scenarios(self, scenarios):
        if not self.target_model_version_id:
            return list(scenarios)
        return [
            scenario
            for scenario in scenarios
            if parse_portrait_payload(
                scenario.subtitle
            ).model_version_id
            == self.target_model_version_id
        ]

    def _apply_target_setup(self) -> None:
        target = self.target_model_version_id
        artifact = self.target_artifact_path
        target_model: EvaluationTextValue = (
            target
            if target
            else evaluation_text("tests.setup.latest_registered")
        )
        artifact_model: EvaluationTextValue = (
            artifact
            if artifact
            else evaluation_text("tests.setup.resolve_from_registry")
        )
        self._setup_models = (
            (
                evaluation_text("tests.setup.goal"),
                evaluation_text("tests.setup.goal.value"),
            ),
            (
                evaluation_text("tests.setup.mode"),
                evaluation_text("tests.setup.mode.value"),
            ),
            (evaluation_text("tests.setup.version"), target_model),
            (evaluation_text("tests.setup.weights"), artifact_model),
            (
                evaluation_text("tests.setup.response"),
                evaluation_text("tests.setup.response.value"),
            ),
        )
        self._sync_setup_compat()
        if target:
            target_context = (
                evaluation_text(
                    "tests.context.selected_lineage",
                    version_id=target,
                ),
                evaluation_text(
                    "tests.context.artifact",
                    artifact=artifact_model,
                ),
            )
            existing = tuple(
                item
                for item in self._context_models
                if not (
                    isinstance(item, EvaluationText)
                    and item.key
                    in {
                        "tests.context.selected_lineage",
                        "tests.context.artifact",
                    }
                )
            )
            self._set_context_models(target_context + existing)

    def _set_service_unavailable(self) -> None:
        self._title_model = evaluation_text("tests.header.title")
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.service_unavailable"
        )
        self._sync_header_compat()
        self.metrics = self._empty_metrics("service_unavailable")
        self.problematic_cases = (
            _evaluation_case(
                evaluation_text("tests.case.service_unavailable.title"),
                (evaluation_text("tests.case.service_unavailable.note"),),
            ),
        )
        self._set_context_models((evaluation_text("tests.context.big_five"),))

    def _set_load_failed(self) -> None:
        self._title_model = evaluation_text("tests.header.title")
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.load_failed"
        )
        self._sync_header_compat()
        self.metrics = self._empty_metrics("load_failed")
        self.problematic_cases = (
            _evaluation_case(
                evaluation_text("tests.case.load_failed.title"),
                (evaluation_text("tests.case.load_failed.note"),),
            ),
        )
        self._set_context_models((evaluation_text("tests.context.big_five"),))

    def _set_empty(self) -> None:
        self._title_model = evaluation_text("tests.header.title")
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.empty"
        )
        self._sync_header_compat()
        self.metrics = self._empty_metrics("empty")
        self.problematic_cases = (
            _evaluation_case(
                evaluation_text("tests.case.empty.title"),
                (evaluation_text("tests.case.empty.note"),),
            ),
        )
        self._set_context_models(
            (
                evaluation_text("tests.context.pack"),
                evaluation_text("tests.context.factors"),
                evaluation_text("tests.context.analysis_next"),
            )
        )

    def _set_target_empty(self) -> None:
        version_id = self.target_model_version_id
        self._title_model = evaluation_text(
            "tests.header.title.version",
            version_id=version_id,
        )
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.target_empty"
        )
        self._sync_header_compat()
        self.metrics = (
            _evaluation_metric(
                evaluation_text("tests.metric.version_runs"),
                "0",
                evaluation_text(
                    "tests.metric.note.version_runs",
                    version_id=version_id,
                ),
            ),
            *self._empty_metrics("target_empty")[1:],
        )
        self.problematic_cases = (
            _evaluation_case(
                evaluation_text("tests.case.target_empty.title"),
                (
                    evaluation_text(
                        "tests.case.target_empty.note",
                        version_id=version_id,
                    ),
                ),
            ),
        )
        self._set_context_models(
            (
                evaluation_text(
                    "tests.context.selected_lineage",
                    version_id=version_id,
                ),
                evaluation_text(
                    "tests.context.artifact",
                    artifact=(
                        self.target_artifact_path
                        or evaluation_text("tests.value.unresolved")
                    ),
                ),
                evaluation_text("tests.context.big_five"),
            )
        )

    @staticmethod
    def _empty_metrics(state: str) -> tuple[EvaluationMetric, ...]:
        (
            run_note_key,
            status_note_key,
            items_note_key,
            errors_note_key,
        ) = _EMPTY_METRIC_NOTE_KEYS[state]
        return (
            _evaluation_metric(
                evaluation_text("tests.metric.runs"),
                "0",
                evaluation_text(run_note_key),
            ),
            _evaluation_metric(
                evaluation_text("tests.metric.latest_status"),
                "—",
                evaluation_text(status_note_key),
            ),
            _evaluation_metric(
                evaluation_text("tests.metric.items"),
                "—",
                evaluation_text(items_note_key),
            ),
            _evaluation_metric(
                evaluation_text("tests.metric.errors"),
                "—",
                evaluation_text(errors_note_key),
            ),
        )

    @staticmethod
    def _summary_model(
        portrait: PortraitRunRecord,
    ) -> EvaluationTextValue:
        if portrait.total:
            return evaluation_text(
                "tests.header.subtitle.summary",
                passed=portrait.passed,
                total=portrait.total,
                model_version=portrait.model_version_id or "—",
            )
        return portrait.raw_summary

    @staticmethod
    def _answers_value(portrait: PortraitRunRecord) -> str:
        if portrait.total:
            return f"{portrait.answer_count}/{portrait.total}"
        return "—"

    @staticmethod
    def _failure_count(
        portrait: PortraitRunRecord,
        status: EvaluationRunStatus,
    ) -> int:
        count = max(
            portrait.invalid_count,
            max(0, portrait.total - portrait.passed),
        )
        if status in {
            EvaluationRunStatus.PARTIAL,
            EvaluationRunStatus.FAILED,
        }:
            return max(1, count)
        return count

    def _case_views(
        self,
        portrait: PortraitRunRecord,
    ) -> tuple[EvaluationCase, ...]:
        return tuple(self._case_view(case) for case in portrait.cases)

    @staticmethod
    def _case_view(case: PortraitCaseRecord) -> EvaluationCase:
        models: list[EvaluationTextValue] = []
        if case.trait:
            models.append(
                evaluation_text("tests.case.field.trait", value=case.trait)
            )
        if case.key:
            models.append(
                evaluation_text(
                    "tests.case.field.key",
                    value=case.key,
                    reverse=1 if case.reverse else 0,
                )
            )
        if case.item:
            models.append(
                evaluation_text("tests.case.field.item", value=case.item)
            )
        if case.raw_status:
            models.append(
                evaluation_text(
                    "tests.case.field.status",
                    status=evaluation_text(
                        _MODEL_STATUS_KEYS[case.status_code]
                    ),
                )
            )
        models.append(
            evaluation_text(
                "tests.case.field.valid",
                value=evaluation_text(
                    "common.yes" if case.valid_score else "common.no"
                ),
            )
        )
        if case.response:
            models.append(
                evaluation_text(
                    "tests.case.field.response",
                    value=case.response,
                )
            )
        if case.raw_response and case.raw_response != case.response:
            models.append(
                evaluation_text(
                    "tests.case.field.raw_response",
                    value=case.raw_response,
                )
            )
        return _evaluation_case(
            evaluation_text(
                "tests.case.title",
                index=case.index,
            ),
            tuple(models) or (case.raw_block,),
        )

    def begin_run(self) -> bool:
        if self.run_in_progress:
            return False
        self.run_in_progress = True
        target = self.target_model_version_id
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.running.version"
            if target
            else "tests.header.subtitle.running.latest",
            version_id=target,
        )
        self.subtitle = _compat_text(self._subtitle_model)
        return True

    def run_tests_sync(self) -> ExperimentRunResult:
        if self.experiments_service is None:
            return experiment_result(
                False,
                message_code="service_unavailable",
            )
        return self.experiments_service.run_personality_portrait_test_pack(
            self.target_model_version_id or None
        )

    def finish_run(self, result: ExperimentRunResult) -> None:
        self.run_in_progress = False
        self.refresh()
        self._run_message_model = self._result_message(result)
        self._subtitle_model = self._run_message_model
        self.subtitle = _compat_text(self._run_message_model)

    @staticmethod
    def _result_message(
        result: ExperimentRunResult,
    ) -> EvaluationTextValue:
        message_key = _RESULT_MESSAGE_KEYS.get(result.message_code.strip())
        if message_key is None:
            return evaluation_text("tests.message.result_unavailable")
        return evaluation_text(
            message_key,
            **dict(result.message_values),
        )

    def header_title_model(self) -> EvaluationTextValue:
        return self._title_model

    def header_subtitle_model(self) -> EvaluationTextValue:
        return self._subtitle_model

    def setup_models(
        self,
    ) -> tuple[tuple[EvaluationText, EvaluationTextValue], ...]:
        return self._setup_models

    @staticmethod
    def metric_title_model(
        metric: EvaluationMetric,
    ) -> EvaluationTextValue:
        return metric.title_model or metric.title

    @staticmethod
    def metric_note_model(
        metric: EvaluationMetric,
    ) -> EvaluationTextValue:
        return metric.note_model or metric.note

    @staticmethod
    def case_title_model(
        case: EvaluationCase,
    ) -> EvaluationTextValue:
        return case.title_model or case.title

    @staticmethod
    def case_note_models(
        case: EvaluationCase,
    ) -> tuple[EvaluationTextValue, ...]:
        return case.note_models or (case.note,)

    def context_models(self) -> tuple[EvaluationTextValue, ...]:
        return self._context_models

    def review_models(self) -> tuple[EvaluationTextValue, ...]:
        rows: list[EvaluationTextValue] = [self._subtitle_model, ""]
        for case in self.problematic_cases:
            rows.append(self.case_title_model(case))
            rows.extend(self.case_note_models(case))
            rows.append("")
        return tuple(rows)

    def review_text(self) -> str:
        lines = [self.subtitle, ""]
        for case in self.problematic_cases:
            lines.append(case.title)
            lines.append(case.note)
            lines.append("")
        return "\n".join(lines).strip()

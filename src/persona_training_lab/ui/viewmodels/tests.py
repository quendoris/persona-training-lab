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
from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)
from persona_training_lab.ui.viewmodels.evaluation import (
    EvaluationText,
    evaluation_status_text,
    evaluation_text,
)


@dataclass(slots=True, frozen=True)
class EvaluationMetric:
    title: str
    value: str
    note: str
    title_model: str | EvaluationText | None = None
    note_model: str | EvaluationText | None = None


@dataclass(slots=True, frozen=True)
class EvaluationCase:
    title: str
    note: str
    title_model: str | EvaluationText | None = None
    note_models: tuple[str | EvaluationText, ...] = ()


@dataclass(slots=True)
class TestsViewModel:
    __test__ = False

    experiments_service: ExperimentsService | None = None
    title: str = "Тесты"
    subtitle: str = "Соберите психологический портрет текущей модели."
    setup_rows: tuple[tuple[str, str], ...] = ()
    metrics: tuple[EvaluationMetric, ...] = ()
    problematic_cases: tuple[EvaluationCase, ...] = ()
    context_rows: tuple[str, ...] = ()
    run_in_progress: bool = False
    target_node_id: str = ""
    target_model_version_id: str = ""
    target_artifact_path: str = ""
    _title_model: str | EvaluationText = field(
        default_factory=lambda: evaluation_text("tests.header.title")
    )
    _subtitle_model: str | EvaluationText = field(
        default_factory=lambda: evaluation_text("tests.header.subtitle.empty")
    )
    _setup_models: tuple[
        tuple[EvaluationText, str | EvaluationText], ...
    ] = ()
    _context_models: tuple[str | EvaluationText, ...] = ()
    _run_message_model: str | EvaluationText | None = None

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
        self.title = f"Тесты · {latest.title}"
        self.subtitle = portrait.raw_summary or latest.subtitle
        self._title_model = evaluation_text(
            "tests.header.title.run",
            title=latest.title,
        )
        self._subtitle_model = self._summary_model(portrait)
        self.metrics = (
            EvaluationMetric(
                "Запусков",
                str(len(matching)),
                "сохранённые portrait/test runs",
                evaluation_text(
                    "tests.metric.version_runs"
                    if self.target_model_version_id
                    else "tests.metric.runs"
                ),
                evaluation_text(
                    "tests.metric.note.version_runs",
                    version_id=self.target_model_version_id,
                )
                if self.target_model_version_id
                else evaluation_text("tests.metric.note.runs"),
            ),
            EvaluationMetric(
                "Последний статус",
                latest.status,
                "последний сохранённый запуск выбранной версии",
                evaluation_text("tests.metric.latest_status"),
                evaluation_text("tests.metric.note.latest_status"),
            ),
            EvaluationMetric(
                "Пункты",
                self._answers_value(portrait),
                "валидные SCORE-ответы",
                evaluation_text("tests.metric.items"),
                evaluation_text("tests.metric.note.items"),
            ),
            EvaluationMetric(
                "Ошибки",
                str(failures),
                "пункты без валидного SCORE",
                evaluation_text("tests.metric.errors"),
                evaluation_text("tests.metric.note.errors"),
            ),
        )
        self.problematic_cases = self._case_views(portrait) or (
            EvaluationCase(
                "Ответы не сохранены",
                "Запустите сбор портрета ещё раз.",
                evaluation_text("tests.case.missing.title"),
                (evaluation_text("tests.case.missing.note"),),
            ),
        )
        self.context_rows = (
            f"Последний портрет · {latest.experiment_id}",
            f"Статус · {latest.status}",
            "Big Five scored items",
            "KPI: средние баллы по факторам с reverse scoring",
        )
        self._context_models = (
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
        target_model: str | EvaluationText = (
            target
            if target
            else evaluation_text("tests.setup.latest_registered")
        )
        artifact_model: str | EvaluationText = (
            artifact
            if artifact
            else evaluation_text("tests.setup.resolve_from_registry")
        )
        self.setup_rows = (
            ("Цель", "Big Five KPI портрет модели"),
            ("Режим", "scored self-report items"),
            ("Версия", target or "последняя зарегистрированная"),
            ("Веса", artifact or "будет разрешён из реестра версий"),
            ("Ответ", "только SCORE: 1-5"),
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
            self._context_models = target_context + existing

    def _set_service_unavailable(self) -> None:
        self.title = "Тесты"
        self.subtitle = "Сервис тестов не подключён"
        self._title_model = evaluation_text("tests.header.title")
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.service_unavailable"
        )
        self.metrics = self._empty_metrics("service_unavailable")
        self.problematic_cases = (
            EvaluationCase(
                "Сервис тестов не подключён",
                "Проверьте wiring приложения.",
                evaluation_text("tests.case.service_unavailable.title"),
                (evaluation_text("tests.case.service_unavailable.note"),),
            ),
        )
        self._context_models = (evaluation_text("tests.context.big_five"),)

    def _set_load_failed(self) -> None:
        self.title = "Тесты"
        self.subtitle = "Не удалось загрузить тесты"
        self._title_model = evaluation_text("tests.header.title")
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.load_failed"
        )
        self.metrics = self._empty_metrics("load_failed")
        self.problematic_cases = (
            EvaluationCase(
                "Не удалось загрузить тесты",
                "Проверьте подключение к базе данных.",
                evaluation_text("tests.case.load_failed.title"),
                (evaluation_text("tests.case.load_failed.note"),),
            ),
        )
        self._context_models = (evaluation_text("tests.context.big_five"),)

    def _set_empty(self) -> None:
        self.title = "Тесты"
        self.subtitle = "Психологический портрет пока не собран"
        self._title_model = evaluation_text("tests.header.title")
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.empty"
        )
        self.metrics = self._empty_metrics("empty")
        self.problematic_cases = (
            EvaluationCase(
                "Портрет пока не собран",
                "Нажмите «Собрать портрет», чтобы получить SCORE-ответы модели.",
                evaluation_text("tests.case.empty.title"),
                (evaluation_text("tests.case.empty.note"),),
            ),
        )
        self.context_rows = (
            "Big Five/IPIP-style scored pack",
            (
                "Факторы: Extraversion, Agreeableness, Conscientiousness, "
                "Emotional Stability, Openness"
            ),
            "Дальше анализ считает средние KPI по факторам",
        )
        self._context_models = (
            evaluation_text("tests.context.pack"),
            evaluation_text("tests.context.factors"),
            evaluation_text("tests.context.analysis_next"),
        )

    def _set_target_empty(self) -> None:
        version_id = self.target_model_version_id
        self.title = f"Тесты · {version_id}"
        self.subtitle = (
            "Для выбранной версии портрет ещё не собран. Другие сохранённые "
            "результаты намеренно не подставляются."
        )
        self._title_model = evaluation_text(
            "tests.header.title.version",
            version_id=version_id,
        )
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.target_empty"
        )
        self.metrics = (
            EvaluationMetric(
                "Запусков версии",
                "0",
                f"для {version_id} нет сохранённых portrait runs",
                evaluation_text("tests.metric.version_runs"),
                evaluation_text(
                    "tests.metric.note.version_runs",
                    version_id=version_id,
                ),
            ),
            *self._empty_metrics("target_empty")[1:],
        )
        self.problematic_cases = (
            EvaluationCase(
                "Портрет выбранной версии не собран",
                (
                    f"Нажмите «Собрать портрет»: тест будет запущен на весах "
                    f"{version_id}, а не на последней модели по умолчанию."
                ),
                evaluation_text("tests.case.target_empty.title"),
                (
                    evaluation_text(
                        "tests.case.target_empty.note",
                        version_id=version_id,
                    ),
                ),
            ),
        )
        self._context_models = (
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

    @staticmethod
    def _empty_metrics(state: str) -> tuple[EvaluationMetric, ...]:
        return (
            EvaluationMetric(
                "Запусков",
                "0",
                "портреты пока не собирались",
                evaluation_text("tests.metric.runs"),
                evaluation_text(f"tests.metric.note.{state}.runs"),
            ),
            EvaluationMetric(
                "Последний статус",
                "—",
                "нет результата",
                evaluation_text("tests.metric.latest_status"),
                evaluation_text(f"tests.metric.note.{state}.status"),
            ),
            EvaluationMetric(
                "Пункты",
                "—",
                "нет результата",
                evaluation_text("tests.metric.items"),
                evaluation_text(f"tests.metric.note.{state}.items"),
            ),
            EvaluationMetric(
                "Ошибки",
                "—",
                "нет результата",
                evaluation_text("tests.metric.errors"),
                evaluation_text(f"tests.metric.note.{state}.errors"),
            ),
        )

    @staticmethod
    def _summary_model(
        portrait: PortraitRunRecord,
    ) -> str | EvaluationText:
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
        legacy_parts: list[str] = []
        models: list[str | EvaluationText] = []
        if case.trait:
            legacy_parts.append(f"Фактор: {case.trait}")
            models.append(
                evaluation_text("tests.case.field.trait", value=case.trait)
            )
        if case.key:
            legacy_parts.append(
                f"Ключ: {case.key} · reverse={1 if case.reverse else 0}"
            )
            models.append(
                evaluation_text(
                    "tests.case.field.key",
                    value=case.key,
                    reverse=1 if case.reverse else 0,
                )
            )
        if case.item:
            legacy_parts.append(f"Пункт: {case.item}")
            models.append(
                evaluation_text("tests.case.field.item", value=case.item)
            )
        if case.raw_status:
            legacy_parts.append(f"Статус: {case.raw_status}")
            models.append(
                evaluation_text(
                    "tests.case.field.status",
                    status=evaluation_text(
                        f"tests.model_status.{case.status_code.value}"
                    ),
                )
            )
        legacy_parts.append(
            f"Валидность: {'да' if case.valid_score else 'нет'}"
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
            legacy_parts.append(f"Ответ: {case.response}")
            models.append(
                evaluation_text(
                    "tests.case.field.response",
                    value=case.response,
                )
            )
        if case.raw_response and case.raw_response != case.response:
            legacy_parts.append(f"Сырой ответ: {case.raw_response}")
            models.append(
                evaluation_text(
                    "tests.case.field.raw_response",
                    value=case.raw_response,
                )
            )
        return EvaluationCase(
            title=f"Пункт {case.index}",
            note="\n".join(legacy_parts) or case.raw_block,
            title_model=evaluation_text(
                "tests.case.title",
                index=case.index,
            ),
            note_models=tuple(models) or (case.raw_block,),
        )

    def begin_run(self) -> bool:
        if self.run_in_progress:
            return False
        self.run_in_progress = True
        target = self.target_model_version_id
        self.subtitle = (
            f"Сбор психологического портрета {target or 'последней версии'} "
            "выполняется…"
        )
        self._subtitle_model = evaluation_text(
            "tests.header.subtitle.running.version"
            if target
            else "tests.header.subtitle.running.latest",
            version_id=target,
        )
        return True

    def run_tests_sync(self) -> ExperimentRunResult:
        if self.experiments_service is None:
            return experiment_result(
                False,
                "Сервис тестов не подключён",
                message_code="service_unavailable",
            )
        return self.experiments_service.run_personality_portrait_test_pack(
            self.target_model_version_id or None
        )

    def finish_run(self, result: ExperimentRunResult) -> None:
        self.run_in_progress = False
        self.refresh()
        self.subtitle = result.message
        self._run_message_model = self._result_message(result)
        self._subtitle_model = self._run_message_model

    @staticmethod
    def _result_message(
        result: ExperimentRunResult,
    ) -> str | EvaluationText:
        if not result.message_code:
            return result.message
        return evaluation_text(
            f"tests.message.{result.message_code}",
            **dict(result.message_values),
        )

    def header_title_model(self) -> str | EvaluationText:
        return self._title_model

    def header_subtitle_model(self) -> str | EvaluationText:
        return self._subtitle_model

    def setup_models(
        self,
    ) -> tuple[tuple[EvaluationText, str | EvaluationText], ...]:
        return self._setup_models

    @staticmethod
    def metric_title_model(
        metric: EvaluationMetric,
    ) -> str | EvaluationText:
        return metric.title_model or metric.title

    @staticmethod
    def metric_note_model(
        metric: EvaluationMetric,
    ) -> str | EvaluationText:
        return metric.note_model or metric.note

    @staticmethod
    def case_title_model(
        case: EvaluationCase,
    ) -> str | EvaluationText:
        return case.title_model or case.title

    @staticmethod
    def case_note_models(
        case: EvaluationCase,
    ) -> tuple[str | EvaluationText, ...]:
        return case.note_models or (case.note,)

    def context_models(self) -> tuple[str | EvaluationText, ...]:
        return self._context_models

    def review_models(self) -> tuple[str | EvaluationText, ...]:
        rows: list[str | EvaluationText] = [self._subtitle_model, ""]
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

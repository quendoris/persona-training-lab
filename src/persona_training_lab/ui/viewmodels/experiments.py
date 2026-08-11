from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.experiments.service import (
    ExperimentSummary,
    ExperimentsService,
)
from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus
from persona_training_lab.ui.viewmodels.evaluation import (
    EvaluationText,
    evaluation_status_text,
    evaluation_text,
)
from persona_training_lab.ui.viewmodels.experiment_semantics import (
    experiment_title_text,
)


@dataclass(slots=True, frozen=True)
class ExperimentView:
    experiment_id: str
    title: str | EvaluationText
    subtitle: str | EvaluationText
    status: str | EvaluationText
    status_code: EvaluationRunStatus = EvaluationRunStatus.UNKNOWN


@dataclass(slots=True)
class ExperimentsViewModel:
    experiments_service: ExperimentsService | None = None
    _experiments: tuple[ExperimentView, ...] = field(default_factory=tuple)
    _current_experiment_id: str = ""

    def __post_init__(self) -> None:
        self._apply_experiments_connector()

    def _apply_experiments_connector(self) -> None:
        if self.experiments_service is None:
            self._experiments = (self._empty_experiment(),)
            self._current_experiment_id = self._experiments[0].experiment_id
            return
        try:
            live = self.experiments_service.list_experiments()
        except Exception:
            self._experiments = (self._error_experiment(),)
            self._current_experiment_id = self._experiments[0].experiment_id
            return

        if not live:
            self._experiments = (self._empty_experiment(),)
            self._current_experiment_id = self._experiments[0].experiment_id
            return

        mapped = tuple(self._map_summary(item) for item in live)
        self._experiments = mapped
        self._current_experiment_id = mapped[0].experiment_id

    @staticmethod
    def _map_summary(summary: ExperimentSummary) -> ExperimentView:
        return ExperimentView(
            experiment_id=summary.experiment_id,
            title=experiment_title_text(summary),
            subtitle=summary.subtitle,
            status=evaluation_status_text(
                summary.status_code,
                summary.status,
            ),
            status_code=summary.status_code,
        )

    @staticmethod
    def _empty_experiment() -> ExperimentView:
        return ExperimentView(
            experiment_id="experiments_empty",
            title=evaluation_text("experiments.empty.title"),
            subtitle=evaluation_text("experiments.empty.subtitle"),
            status=evaluation_text("experiments.empty.status"),
        )

    @staticmethod
    def _error_experiment() -> ExperimentView:
        return ExperimentView(
            experiment_id="experiments_error",
            title=evaluation_text("experiments.error.title"),
            subtitle=evaluation_text("experiments.error.subtitle"),
            status=evaluation_text("experiments.error.status"),
        )

    def experiments(
        self,
    ) -> list[
        tuple[
            str,
            str | EvaluationText,
            str | EvaluationText,
            str | EvaluationText,
        ]
    ]:
        return [
            (e.experiment_id, e.title, e.subtitle, e.status)
            for e in self._experiments
        ]

    def current_experiment(self) -> ExperimentView:
        for item in self._experiments:
            if item.experiment_id == self._current_experiment_id:
                return item
        return self._experiments[0]

    def header_summary(
        self,
    ) -> tuple[str | EvaluationText, str | EvaluationText]:
        current = self.current_experiment()
        return current.title, current.subtitle

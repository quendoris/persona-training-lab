from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.experiments.service import ExperimentSummary, ExperimentsService


@dataclass(slots=True, frozen=True)
class ExperimentView:
    experiment_id: str
    title: str
    subtitle: str
    status: str


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
            title=summary.title,
            subtitle=summary.subtitle,
            status=summary.status,
        )

    @staticmethod
    def _empty_experiment() -> ExperimentView:
        return ExperimentView(
            experiment_id="experiments_empty",
            title="Эксперименты пока не созданы",
            subtitle="Эксперименты пока не созданы",
            status="пусто",
        )

    @staticmethod
    def _error_experiment() -> ExperimentView:
        return ExperimentView(
            experiment_id="experiments_error",
            title="Не удалось загрузить эксперименты",
            subtitle="Не удалось загрузить эксперименты",
            status="ошибка",
        )

    def experiments(self) -> list[tuple[str, str, str, str]]:
        return [(e.experiment_id, e.title, e.subtitle, e.status) for e in self._experiments]

    def current_experiment(self) -> ExperimentView:
        for item in self._experiments:
            if item.experiment_id == self._current_experiment_id:
                return item
        return self._experiments[0]

    def header_summary(self) -> tuple[str, str]:
        current = self.current_experiment()
        return current.title, current.subtitle

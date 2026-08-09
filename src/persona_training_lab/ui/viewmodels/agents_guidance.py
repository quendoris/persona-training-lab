from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.agents.service import AgentSummary, AgentsService
from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.experiments.portrait import parse_portrait_payload
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentRoleView,
    AgentView,
    PortraitStats,
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


@dataclass(slots=True)
class AgentsGuidanceViewModel:
    """Live Agents guidance over service read models."""

    agents_service: AgentsService | None = None
    training_service: TrainingService | None = None
    model_versions_service: ModelVersionsService | None = None
    datasets_service: DatasetsService | None = None
    experiments_service: ExperimentsService | None = None
    _agents: tuple[AgentView, ...] = field(default_factory=tuple)
    _current_agent_id: str = ""

    def __post_init__(self) -> None:
        self._apply_agents_connector()

    def _apply_agents_connector(self) -> None:
        if self.agents_service is None:
            self._agents = (self._empty_agent(),)
            self._current_agent_id = self._agents[0].agent_id
            return
        try:
            live_agents = self.agents_service.list_agents()
        except Exception:
            self._agents = (self._error_agent(),)
            self._current_agent_id = self._agents[0].agent_id
            return

        if not live_agents:
            self._agents = (self._empty_agent(),)
            self._current_agent_id = self._agents[0].agent_id
            return

        mapped = tuple(self._map_summary(item) for item in live_agents)
        self._agents = mapped
        self._current_agent_id = mapped[0].agent_id

    @staticmethod
    def _map_summary(summary: AgentSummary) -> AgentView:
        return AgentView(
            agent_id=summary.agent_id,
            title=summary.title,
            subtitle=summary.subtitle,
            status=summary.status,
        )

    @staticmethod
    def _empty_agent() -> AgentView:
        return AgentView(
            agent_id="agents_empty",
            title="Системные роли готовы",
            subtitle=(
                "База агентов пуста, но рабочие роли доступны как встроенный "
                "навигатор."
            ),
            status="локально",
        )

    @staticmethod
    def _error_agent() -> AgentView:
        return AgentView(
            agent_id="agents_error",
            title="Не удалось загрузить агентов",
            subtitle=(
                "База ролей недоступна, используются встроенные подсказки."
            ),
            status="ошибка",
        )

    def agents(self) -> list[tuple[str, str, str, str]]:
        return [
            (agent.agent_id, agent.title, agent.subtitle, agent.status)
            for agent in self._agents
        ]

    def current_agent(self) -> AgentView:
        for agent in self._agents:
            if agent.agent_id == self._current_agent_id:
                return agent
        return self._agents[0]

    def header_summary(self) -> tuple[str, str]:
        return (
            "Агенты",
            "Рабочий центр версий: роли подсказывают, lineage показывает "
            "состояние модели.",
        )

    def roles(self) -> tuple[AgentRoleView, ...]:
        next_step = self.next_best_step()
        latest = self._latest_portrait()
        delta = self.delta_line() or "нужен второй портрет"
        dataset_note = self._dataset_note()
        return (
            AgentRoleView(
                "version_navigator",
                "Версионный навигатор",
                "Видит дерево model lineage и не даёт потерять актуальную версию.",
                next_step,
                "главный",
            ),
            AgentRoleView(
                "researcher",
                "Исследователь",
                "Объясняет KPI и delta между портретами.",
                f"Текущая delta: {delta}",
                "анализ",
            ),
            AgentRoleView(
                "dataset_auditor",
                "Аудитор датасета",
                "Проверяет структурную готовность обучающих данных.",
                dataset_note,
                "проверка",
            ),
            AgentRoleView(
                "protocolist",
                "Протоколист",
                "Напоминает, что фиксировать для воспроизводимости.",
                "Фиксируйте model, dataset, battery, scoring и raw responses.",
                "протокол",
            ),
            AgentRoleView(
                "labeler",
                "Разметчик",
                "Готовит будущий corrective dataset по ошибкам и слабым факторам.",
                self._labeler_step(latest),
                "позже",
            ),
        )

    def next_best_step(self) -> str:
        datasets = self._datasets()
        runs = self._training_runs()
        versions = self._model_versions()
        portraits = self._portraits()
        latest = self._portrait_stats(portraits[0]) if portraits else None
        if not datasets:
            return "Добавьте датасет и проверьте структуру."
        if not any(
            getattr(item, "status", "") == "Одобрен для обучения"
            for item in datasets
        ):
            return "Одобрите валидный датасет для обучения."
        if not runs:
            return "Создайте training run."
        if (
            not getattr(runs[0], "artifact_path", "")
            and getattr(runs[0], "status", "")
            not in {"Завершён", "Готово", "Готова"}
        ):
            return "Доведите training run до artifact."
        if not versions:
            return "Создайте snapshot/model version из artifact."
        if latest is None:
            return "Соберите Big Five portrait текущей модели."
        if latest.failures > 0:
            return "Повторите портрет: есть invalid SCORE."
        if len(portraits) < 2:
            return (
                "После следующего fine-tune соберите второй портрет для delta."
            )
        return "Откройте анализ и сравните latest - previous."

    def delta_line(self) -> str:
        portraits = self._portraits()
        if len(portraits) < 2:
            return ""
        latest = self._portrait_stats(portraits[0])
        previous = self._portrait_stats(portraits[1])
        parts = []
        for key in TRAIT_ORDER:
            if key in latest.scores and key in previous.scores:
                parts.append(
                    f"{TRAIT_LABELS[key]}="
                    f"{latest.scores[key] - previous.scores[key]:+.2f}"
                )
        return " · ".join(parts)

    def _training_runs(self) -> list[object]:
        if self.training_service is None:
            return []
        try:
            return self.training_service.list_training_runs()
        except Exception:
            return []

    def _model_versions(self) -> list[object]:
        if self.model_versions_service is None:
            return []
        try:
            return self.model_versions_service.list_model_versions()
        except Exception:
            return []

    def _datasets(self) -> list[object]:
        if self.datasets_service is None:
            return []
        try:
            return self.datasets_service.list_datasets()
        except Exception:
            return []

    def _portraits(self) -> list[object]:
        if self.experiments_service is None:
            return []
        try:
            return self.experiments_service.list_experiments()
        except Exception:
            return []

    def _latest_portrait(self) -> PortraitStats | None:
        portraits = self._portraits()
        return self._portrait_stats(portraits[0]) if portraits else None

    def _portrait_stats(self, experiment: object) -> PortraitStats:
        portrait = parse_portrait_payload(getattr(experiment, "subtitle", ""))
        invalid = sum(
            1
            for case in portrait.cases
            if case.score is None or not case.valid_score
        )
        failures = (
            max(invalid, max(0, portrait.total - portrait.passed))
            if portrait.total
            else invalid
        )
        return PortraitStats(
            title=getattr(experiment, "title", ""),
            passed=portrait.passed,
            total=portrait.total,
            failures=failures,
            scores=portrait.trait_scores(),
        )

    def _score_line(self, scores: dict[str, float]) -> str:
        return " · ".join(
            f"{TRAIT_LABELS[key]}={scores[key]:.2f}"
            for key in TRAIT_ORDER
            if key in scores
        )

    def _dataset_note(self) -> str:
        datasets = self._datasets()
        if not datasets:
            return "Датасет не добавлен."
        approved = sum(
            1
            for item in datasets
            if getattr(item, "status", "") == "Одобрен для обучения"
        )
        errors = sum(
            1
            for item in datasets
            if getattr(item, "invalid_count", 0) > 0
        )
        return (
            f"Датасеты: {len(datasets)} · одобрено {approved} · "
            f"с ошибками {errors}."
        )

    def _labeler_step(self, latest: PortraitStats | None) -> str:
        if latest is None:
            return (
                "Сначала соберите портрет, потом размечайте слабые факторы."
            )
        if latest.failures > 0:
            return (
                "Сначала уберите invalid SCORE, потом собирайте corrective dataset."
            )
        weakest = (
            min(latest.scores.items(), key=lambda item: item[1])
            if latest.scores
            else None
        )
        if weakest is None:
            return "Нет KPI для разметки."
        return (
            "Начните corrective dataset со слабого фактора: "
            f"{weakest[0]}={weakest[1]:.2f}."
        )


__all__ = ("AgentsGuidanceViewModel",)

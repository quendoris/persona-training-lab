from __future__ import annotations

from dataclasses import dataclass, field
import re

from persona_training_lab.application.agents.service import AgentSummary, AgentsService
from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentRoleView,
    AgentView,
    PortraitStats,
)


SCORE_RE = re.compile(r"\bSCORE\s*:\s*([1-5])\b", re.IGNORECASE)
CASE_HEADER_RE = re.compile(r"(?m)^CASE\s+\d+")
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
        subtitle = getattr(experiment, "subtitle", "")
        title = getattr(experiment, "title", "")
        passed, total = self._parse_passed_total(subtitle)
        values, invalid = self._parse_scores(subtitle)
        failures = max(invalid, max(0, total - passed)) if total else invalid
        return PortraitStats(
            title=title,
            passed=passed,
            total=total,
            failures=failures,
            scores={
                trait: round(sum(items) / len(items), 2)
                for trait, items in values.items()
                if items
            },
        )

    def _parse_scores(
        self,
        subtitle: str,
    ) -> tuple[dict[str, list[float]], int]:
        values: dict[str, list[float]] = {}
        invalid = 0
        for block in self._split_case_records(subtitle):
            lines = [
                line.strip()
                for line in block.splitlines()
                if line.strip()
            ]
            trait = self._field(lines, "TRAIT")
            reverse = self._field(lines, "REVERSE") == "1"
            valid_score = self._field(lines, "VALID_SCORE")
            response = self._field(lines, "RESPONSE")
            score = self._score_from_response(response)
            if score is None or valid_score == "0":
                invalid += 1
                continue
            final_score = 6 - score if reverse else score
            if trait:
                values.setdefault(trait, []).append(float(final_score))
        return values, invalid

    def _split_case_records(self, subtitle: str) -> list[str]:
        match = CASE_HEADER_RE.search(subtitle)
        if match is None:
            return []
        tail = subtitle[match.start() :]
        records = [
            record.strip()
            for record in CASE_HEADER_RE.split(tail)
            if record.strip()
        ]
        headers = CASE_HEADER_RE.findall(tail)
        return [
            f"{header}\n{record}"
            for header, record in zip(headers, records, strict=False)
        ]

    def _field(self, lines: list[str], name: str) -> str:
        prefix = f"{name}: "
        return next(
            (
                line.removeprefix(prefix).strip()
                for line in lines
                if line.startswith(prefix)
            ),
            "",
        )

    def _score_from_response(self, response: str) -> int | None:
        match = SCORE_RE.search(response)
        return int(match.group(1)) if match else None

    def _parse_passed_total(self, subtitle: str) -> tuple[int, int]:
        summary = subtitle.split("CASE ", 1)[0]
        marker = (
            summary.replace("PORTRAIT:", "")
            .replace("SUMMARY:", "")
            .strip()
            .split(" ")[0]
        )
        if "/" not in marker:
            return 0, 0
        left, right = marker.split("/", 1)
        try:
            return int(left), int(right)
        except ValueError:
            return 0, 0

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

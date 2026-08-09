from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.agents.service import AgentSummary, AgentsService
from persona_training_lab.ui.viewmodels.agents_contracts import AgentView


@dataclass(slots=True)
class AgentsOverviewViewModel:
    """Stable Agents identity/header read model without lineage guidance reads."""

    agents_service: AgentsService | None = None
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


__all__ = ("AgentsOverviewViewModel",)

from __future__ import annotations

from dataclasses import dataclass, field

from persona_training_lab.application.agents.service import AgentSummary, AgentsService
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.i18n.text import render_user_message
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
            title=UserMessage("agents.overview.empty.title"),
            subtitle=UserMessage("agents.overview.empty.subtitle"),
            status=UserMessage("agents.overview.empty.status"),
        )

    @staticmethod
    def _error_agent() -> AgentView:
        return AgentView(
            agent_id="agents_error",
            title=UserMessage("agents.overview.error.title"),
            subtitle=UserMessage("agents.overview.error.subtitle"),
            status=UserMessage("agents.overview.error.status"),
        )

    def agents(self) -> list[tuple[str, str, str, str]]:
        """Base-locale compatibility surface for historical callers."""

        return [
            (
                agent.agent_id,
                render_user_message(None, agent.title),
                render_user_message(None, agent.subtitle),
                render_user_message(None, agent.status),
            )
            for agent in self._agents
        ]

    def current_agent(self) -> AgentView:
        for agent in self._agents:
            if agent.agent_id == self._current_agent_id:
                return agent
        return self._agents[0]

    def header_summary(self) -> tuple[str, str]:
        """Base-locale compatibility surface for historical callers."""

        return (
            render_user_message(None, UserMessage("agents.header.title")),
            render_user_message(None, UserMessage("agents.header.subtitle")),
        )


__all__ = ("AgentsOverviewViewModel",)

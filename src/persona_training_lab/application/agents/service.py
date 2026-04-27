from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.ports.repositories import AgentsReadRepositoryPort


@dataclass(slots=True, frozen=True)
class AgentSummary:
    agent_id: str
    title: str
    subtitle: str
    status: str


@dataclass(slots=True)
class AgentsService:
    agents_repo: AgentsReadRepositoryPort

    def list_agents(self) -> list[AgentSummary]:
        rows = self.agents_repo.list_agents()
        return [
            AgentSummary(
                agent_id=row.get("agent_id", ""),
                title=row.get("title", ""),
                subtitle=row.get("subtitle", ""),
                status=row.get("status", ""),
            )
            for row in rows
        ]

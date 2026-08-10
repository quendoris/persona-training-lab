from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from persona_training_lab.application.messages import UserMessage


AgentText: TypeAlias = UserMessage | str


@dataclass(slots=True, frozen=True)
class AgentView:
    agent_id: str
    title: AgentText
    subtitle: AgentText
    status: AgentText


@dataclass(slots=True, frozen=True)
class AgentRoleView:
    role_id: str
    title: AgentText
    mission: AgentText
    next_action: AgentText
    status: AgentText


@dataclass(slots=True, frozen=True)
class VersionNodeView:
    node_id: str
    depth: int
    title: AgentText
    subtitle: AgentText
    status: AgentText
    tone: str = "neutral"
    branch_note: str = "main"


@dataclass(slots=True, frozen=True)
class AgentDetailView:
    title: AgentText
    body: AgentText
    checks: tuple[AgentText, ...]
    actions: tuple[AgentText, ...] = ()
    action_codes: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PortraitStats:
    title: str
    passed: int
    total: int
    failures: int
    scores: dict[str, float]


__all__ = (
    "AgentDetailView",
    "AgentRoleView",
    "AgentText",
    "AgentView",
    "PortraitStats",
    "VersionNodeView",
)

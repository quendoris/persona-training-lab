from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AgentView:
    agent_id: str
    title: str
    subtitle: str
    status: str


@dataclass(slots=True, frozen=True)
class AgentRoleView:
    role_id: str
    title: str
    mission: str
    next_action: str
    status: str


@dataclass(slots=True, frozen=True)
class VersionNodeView:
    node_id: str
    depth: int
    title: str
    subtitle: str
    status: str
    tone: str = "neutral"
    branch_note: str = "main"


@dataclass(slots=True, frozen=True)
class AgentDetailView:
    title: str
    body: str
    checks: tuple[str, ...]
    actions: tuple[str, ...] = ()


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
    "AgentView",
    "PortraitStats",
    "VersionNodeView",
)

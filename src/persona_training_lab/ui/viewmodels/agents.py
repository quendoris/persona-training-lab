from __future__ import annotations

from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentDetailView,
    AgentRoleView,
    AgentView,
    PortraitStats,
    VersionNodeView,
)
from persona_training_lab.ui.viewmodels.agents_guidance import (
    CASE_HEADER_RE,
    SCORE_RE,
    TRAIT_LABELS,
    TRAIT_ORDER,
)


def __getattr__(name: str):
    if name != "AgentsViewModel":
        raise AttributeError(name)
    from persona_training_lab.ui.viewmodels.agents_legacy import (
        AgentsViewModel,
    )

    return AgentsViewModel


__all__ = (
    "AgentDetailView",
    "AgentRoleView",
    "AgentsViewModel",
    "AgentView",
    "CASE_HEADER_RE",
    "PortraitStats",
    "SCORE_RE",
    "TRAIT_LABELS",
    "TRAIT_ORDER",
    "VersionNodeView",
)

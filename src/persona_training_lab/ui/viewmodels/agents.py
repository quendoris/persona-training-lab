from __future__ import annotations

from typing import TYPE_CHECKING

from persona_training_lab.application.experiments.portrait import (
    CASE_HEADER_RE,
    SCORE_RE,
)
from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentDetailView,
    AgentRoleView,
    AgentView,
    PortraitStats,
    VersionNodeView,
)
from persona_training_lab.ui.viewmodels.agents_guidance import (
    TRAIT_LABELS,
    TRAIT_ORDER,
)

if TYPE_CHECKING:
    from persona_training_lab.ui.viewmodels.agents_legacy import AgentsViewModel


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

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from persona_training_lab.application.experiments.portrait import (
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

# Historical public regex retained only for callers of this compatibility facade.
# Current portrait parsing lives exclusively in application.experiments.portrait.
CASE_HEADER_RE = re.compile(r"(?m)^CASE\s+\d+")

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

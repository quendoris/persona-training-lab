from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageProjectionService,
    AtomicLineageSnapshot,
)
from persona_training_lab.application.lineage.loader import LineageLoaderFactory
from persona_training_lab.ui.viewmodels.agents import (
    AgentsViewModel as _LegacyAgentsViewModel,
)


@dataclass(slots=True)
class AgentsViewModel(_LegacyAgentsViewModel):
    """Agents read model with explicit legacy and worker-owned lineage ports."""

    lineage_projection_service: AtomicLineageProjectionService | None = None
    lineage_loader_factory: LineageLoaderFactory | None = None

    def build_lineage_snapshot(self) -> AtomicLineageSnapshot:
        service = self.lineage_projection_service
        if service is None:
            raise RuntimeError("Atomic lineage projection service is not configured")
        return service.build_snapshot()

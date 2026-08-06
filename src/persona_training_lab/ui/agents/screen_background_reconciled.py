from __future__ import annotations

from persona_training_lab.ui.agents.screen_background import (
    AgentsScreen as _BackgroundAgentsScreen,
)


class AgentsScreen(_BackgroundAgentsScreen):
    """Keep persisted projection safety links equal to the visible projection."""

    def __init__(self, *args, **kwargs) -> None:
        self._bound_projection_node_ids: tuple[str, ...] | None = None
        super().__init__(*args, **kwargs)

    def _bind_projection_resources(self) -> None:
        safety = self._lineage_runtime_safety
        projection = self._real_projection
        if safety is None or projection is None:
            return
        coordinator = self._lineage_refresh_coordinator
        if coordinator is not None and coordinator.last_good is None:
            # Initial placeholders are UI-only. Never clear the last persisted
            # safety registry before the first successful atomic refresh.
            return
        self._bound_projection_node_ids = safety.reconcile_projection(
            projection.resources,
            self._bound_projection_node_ids,
        )

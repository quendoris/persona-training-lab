from __future__ import annotations

from persona_training_lab.ui.agents.lineage import build_version_lineage
from persona_training_lab.ui.agents.refresh_worker import (
    LineageRefreshResult,
    LineageRevisionSet,
)
from persona_training_lab.ui.agents.screen_background_reconciled import (
    AgentsScreen as _BackgroundAgentsScreen,
)


class AgentsScreen(_BackgroundAgentsScreen):
    """Apply content-only lineage changes without resetting canvas geometry."""

    def __init__(self, *args, **kwargs) -> None:
        self._lineage_revisions: LineageRevisionSet | None = None
        super().__init__(*args, **kwargs)
        coordinator = self._lineage_refresh_coordinator
        if coordinator is not None and coordinator.last_good is not None:
            self._lineage_revisions = coordinator.last_good.revisions

    def _on_projection_ready(self, result: LineageRefreshResult) -> None:
        previous = self._lineage_revisions
        if previous == result.revisions:
            self._refresh_runtime_blockers(force=False)
            return

        requires_full_update = (
            previous is None
            or previous.topology != result.revisions.topology
            or previous.presentation != result.revisions.presentation
        )
        if requires_full_update:
            self._apply_projection(result.projection)
        elif not self._apply_projection_content(result):
            self._apply_projection(result.projection)

        self._lineage_revisions = result.revisions
        self._refresh_projection_roles()
        self._refresh_runtime_blockers(force=True)

    def _apply_projection_content(
        self,
        result: LineageRefreshResult,
    ) -> bool:
        projection = result.projection
        next_nodes = self._state.apply(
            build_version_lineage(projection.nodes)
        )
        updater = getattr(self._graph, "update_node_content", None)
        if not callable(updater) or not updater(next_nodes):
            return False

        selected = getattr(self, "_selected_node_id", "")
        self._real_projection = projection
        self._real_projection_signature = projection.signature
        self._lineage_nodes = next_nodes
        self._bind_projection_resources()
        if selected and self._node_by_id(selected) is not None:
            self._select_node(selected)
        return True

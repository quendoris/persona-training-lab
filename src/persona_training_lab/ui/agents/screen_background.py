from __future__ import annotations

from PySide6.QtGui import QHideEvent, QShowEvent

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.ui.agents.atomic_lineage_public import (
    build_empty_lineage,
)
from persona_training_lab.ui.agents.lineage import build_version_lineage
from persona_training_lab.ui.agents.refresh_coordinator import (
    LineageRefreshCoordinator,
)
from persona_training_lab.ui.agents.refresh_worker import (
    LineageRefreshFailure,
    LineageRefreshResult,
)
from persona_training_lab.ui.agents.screen_runtime_safe import (
    AgentsScreen as _RuntimeSafeAgentsScreen,
)
from persona_training_lab.ui.keybindings.manager import KeyBindingManager


class AgentsScreen(_RuntimeSafeAgentsScreen):
    """Runtime-safe Agents UI fed by a worker-owned atomic projection."""

    def __init__(
        self,
        view_model,
        key_binding_manager: KeyBindingManager | None = None,
        lineage_runtime_safety: LineageRuntimeSafety | None = None,
        lineage_refresh_coordinator: LineageRefreshCoordinator | None = None,
    ) -> None:
        self._lineage_refresh_coordinator = lineage_refresh_coordinator
        super().__init__(
            view_model,
            key_binding_manager,
            lineage_runtime_safety,
        )
        coordinator = self._lineage_refresh_coordinator
        if coordinator is None:
            return
        self._runtime_safety_timer.stop()
        coordinator.projection_ready.connect(self._on_projection_ready)
        coordinator.refresh_failed.connect(self._on_projection_failed)
        last_good = coordinator.last_good
        if last_good is not None:
            self._on_projection_ready(last_good)

    def _build_nodes(self):
        coordinator = self._lineage_refresh_coordinator
        if coordinator is None:
            return super()._build_nodes()
        result = coordinator.last_good
        projection = (
            result.projection if result is not None else build_empty_lineage()
        )
        self._real_projection = projection
        self._real_projection_signature = projection.signature
        return self._state.apply(build_version_lineage(projection.nodes))

    def _refresh_runtime_safety(self, *, force: bool = False) -> None:
        if self._lineage_refresh_coordinator is None:
            super()._refresh_runtime_safety(force=force)
            return
        self._refresh_runtime_blockers(force=force)

    def _refresh_runtime_blockers(self, *, force: bool = False) -> None:
        node_id = getattr(self, "_selected_node_id", "")
        node = self._node_by_id(node_id) if node_id else None
        if node is None:
            return
        node_ids = (
            self._state.custom_subtree_ids(node_id)
            if self._state.is_custom_node(node_id)
            else (node_id,)
        )
        blockers = self._deletion_blockers(node_ids)
        signature = tuple(
            sorted(
                (
                    blocker.operation.operation_id,
                    blocker.claim.resource_kind,
                    blocker.claim.resource_id,
                )
                for blocker in blockers
            )
        )
        if not force and signature == self._runtime_blocker_signature:
            return
        self._runtime_blocker_signature = signature
        self._select_node(node_id)

    def request_projection_refresh(self, *, force: bool = True) -> None:
        coordinator = self._lineage_refresh_coordinator
        if coordinator is not None:
            coordinator.request_refresh(force=force)

    def showEvent(self, event: QShowEvent) -> None:  # type: ignore[override]
        super().showEvent(event)
        coordinator = self._lineage_refresh_coordinator
        if coordinator is not None:
            coordinator.set_active(True)

    def hideEvent(self, event: QHideEvent) -> None:  # type: ignore[override]
        coordinator = self._lineage_refresh_coordinator
        if coordinator is not None:
            coordinator.set_active(False)
        super().hideEvent(event)

    def _on_projection_ready(self, result: LineageRefreshResult) -> None:
        projection = result.projection
        if projection.signature != self._real_projection_signature:
            self._apply_projection(projection)
        else:
            self._real_projection = projection
            self._bind_projection_resources()
        self._refresh_runtime_blockers(force=True)

    def _on_projection_failed(self, failure: LineageRefreshFailure) -> None:
        window = self.window()
        status = getattr(window, "_status", None)
        setter = getattr(status, "set_message", None)
        if callable(setter):
            setter(
                "Lineage refresh не обновлён; сохранён последний "
                f"согласованный снимок ({failure.error_type})."
            )

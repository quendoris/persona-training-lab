from __future__ import annotations

from PySide6.QtCore import QTimer

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.lineage import build_version_lineage
from persona_training_lab.ui.agents.real_lineage import (
    RealLineageProjection,
    build_real_lineage,
)
from persona_training_lab.ui.agents.screen_agents_final import (
    AgentsScreen as _FinalAgentsScreen,
)
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


class AgentsScreen(_FinalAgentsScreen):
    """Final agents workspace backed by real persisted lineage and leases."""

    _RUNTIME_REFRESH_MS = 1_200
    _CANONICAL_NODE_IDS = frozenset(
        {"base", "dataset", "training", "snapshot", "portrait", "delta"}
    )

    def __init__(
        self,
        view_model,
        key_binding_manager: KeyBindingManager | None = None,
        lineage_runtime_safety: LineageRuntimeSafety | None = None,
    ) -> None:
        self._lineage_runtime_safety = lineage_runtime_safety
        self._runtime_blocker_signature: tuple[tuple[str, str, str], ...] = ()
        self._real_projection: RealLineageProjection | None = None
        self._real_projection_signature: tuple[
            tuple[str, str, str, str], ...
        ] = ()
        super().__init__(view_model, key_binding_manager)
        self._runtime_safety_timer = QTimer(self)
        self._runtime_safety_timer.setInterval(self._RUNTIME_REFRESH_MS)
        self._runtime_safety_timer.timeout.connect(
            self._refresh_runtime_safety
        )
        self._runtime_safety_timer.start()
        self._bind_projection_resources()
        self._refresh_runtime_safety(force=True)

    def _build_nodes(self):
        projection = build_real_lineage(self._vm)
        self._real_projection = projection
        self._real_projection_signature = projection.signature
        return self._state.apply(build_version_lineage(projection.nodes))

    def _detail_for(self, node_id: str) -> AgentDetailView:
        projection = self._real_projection
        if (
            projection is not None
            and node_id not in self._CANONICAL_NODE_IDS
            and node_id in projection.details
            and not self._state.is_custom_node(node_id)
        ):
            return projection.details[node_id]
        return super()._detail_for(node_id)

    def _continue_from_selected(self) -> None:
        parent_id = getattr(self, "_selected_node_id", "")
        fallback_claims = self._runtime_claims_for_node(parent_id)
        super()._continue_from_selected()
        child_id = getattr(self, "_selected_node_id", "")
        safety = self._lineage_runtime_safety
        if safety is None or not child_id:
            return
        if self._state.is_custom_node(parent_id):
            safety.inherit_node(
                child_id,
                parent_id,
                fallback_claims=fallback_claims,
            )
        else:
            safety.bind_node(child_id, fallback_claims)
        self._refresh_runtime_safety(force=True)

    def _delete_local_branch_subtree(self, node_id: str) -> None:
        removed_ids = self._state.custom_subtree_ids(node_id)
        if not removed_ids:
            return
        blockers = self._deletion_blockers(removed_ids)
        if blockers:
            self._show_runtime_blockers(blockers)
            return

        super()._delete_local_branch_subtree(node_id)
        if self._state.is_custom_node(node_id):
            # Confirmation was cancelled; dependency links stay untouched.
            return
        safety = self._lineage_runtime_safety
        if safety is not None:
            safety.forget_nodes(removed_ids)
        self._refresh_runtime_safety(force=True)

    def _sync_detail_actions(
        self,
        node_id: str,
        *,
        is_custom: bool,
        is_current: bool,
        is_archived: bool,
    ) -> None:
        super()._sync_detail_actions(
            node_id,
            is_custom=is_custom,
            is_current=is_current,
            is_archived=is_archived,
        )
        context = self._node_context(node_id)
        if context.get("node_kind") == "model_version" and not is_custom:
            self._make_current_action.setEnabled(
                not is_current and not is_archived
            )
            self._compare_action.setEnabled(not is_current)
            self._portrait_action.setEnabled(True)
            self._branch_action.setEnabled(not is_archived)
            self._delete_action.setEnabled(False)
            self._delete_action.setToolTip(
                "Зарегистрированные model versions удаляются только через "
                "отдельную транзакцию хранения, не из локального lineage."
            )

        if not is_custom:
            return
        subtree_ids = self._state.custom_subtree_ids(node_id)
        blockers = self._deletion_blockers(subtree_ids)
        if not blockers:
            return
        self._delete_action.setEnabled(False)
        self._delete_action.setToolTip(
            "Удаление временно заблокировано активной операцией: "
            + self._lineage_runtime_safety.blocker_text(blockers)
        )

    def _render_detail(self, detail: AgentDetailView) -> None:
        super()._render_detail(detail)
        context = self._node_context(
            getattr(self, "_selected_node_id", "")
        )
        kind = context.get("node_kind", "")
        if kind:
            self._detail_type_value.setText(
                {
                    "base_model": "Базовая модель",
                    "dataset": "Набор данных",
                    "training_run": "Реальный запуск обучения",
                    "model_version": "Снимок весов / model version",
                    "experiment": "Реальный тест / портрет",
                    "analysis_delta": "Сравнение реальных тестов",
                }.get(kind, self._detail_type_value.text())
            )
        self._apply_runtime_dependency_text()

    def _refresh_runtime_safety(self, *, force: bool = False) -> None:
        if not self.isVisible() and not force:
            return
        projection = build_real_lineage(self._vm)
        if force or projection.signature != self._real_projection_signature:
            self._apply_projection(projection)

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

    def _apply_projection(self, projection: RealLineageProjection) -> None:
        selected = getattr(self, "_selected_node_id", "")
        self._real_projection = projection
        self._real_projection_signature = projection.signature
        self._lineage_nodes = self._state.apply(
            build_version_lineage(projection.nodes)
        )
        self._graph.set_nodes(self._lineage_nodes)
        node_ids = {node.node_id for node in self._lineage_nodes}
        if selected not in node_ids:
            selected = self._graph.current_node_id()
            if selected not in node_ids and self._lineage_nodes:
                selected = self._lineage_nodes[0].node_id
            self._selected_node_id = selected
        self._bind_projection_resources()
        if selected:
            self._select_node(selected)

    def _apply_runtime_dependency_text(self) -> None:
        safety = self._lineage_runtime_safety
        node_id = getattr(self, "_selected_node_id", "")
        if safety is None or not node_id:
            return
        node_ids = (
            self._state.custom_subtree_ids(node_id)
            if self._state.is_custom_node(node_id)
            else (node_id,)
        )
        blockers = self._deletion_blockers(node_ids)
        if blockers:
            base = self._detail_dependency.text().strip()
            runtime_text = (
                "Активная операция удерживает эту точку или её зависимость: "
                + safety.blocker_text(blockers)
                + ". Интерфейс остаётся доступен, но разрушительные действия "
                "временно отключены."
            )
            self._detail_dependency.setText(
                f"{base}\n\n{runtime_text}" if base else runtime_text
            )
            return

        links = safety.links_for_node(node_id)
        if links:
            base = self._detail_dependency.text().strip()
            linked = ", ".join(
                f"{claim.resource_kind}={claim.resource_id}"
                for claim in links
            )
            self._detail_dependency.setText(
                f"{base}\n\nСвязанные реальные ресурсы: {linked}."
            )

    def _show_runtime_blockers(self, blockers) -> None:
        safety = self._lineage_runtime_safety
        if safety is None:
            return
        message = (
            "Удаление не выполнено: точка используется активной операцией. "
            + safety.blocker_text(blockers)
        )
        self._detail_dependency.setText(message)
        self._delete_action.setEnabled(False)
        self._delete_action.setToolTip(message)
        window = self.window()
        status = getattr(window, "_status", None)
        setter = getattr(status, "set_message", None)
        if callable(setter):
            setter(message)

    def _deletion_blockers(self, node_ids):
        safety = self._lineage_runtime_safety
        if safety is None:
            return ()
        return safety.deletion_blockers(node_ids)

    def _bind_projection_resources(self) -> None:
        safety = self._lineage_runtime_safety
        projection = self._real_projection
        if safety is None or projection is None:
            return
        for node_id, claims in projection.resources.items():
            safety.bind_node(node_id, claims)

    def _runtime_claims_for_node(
        self,
        node_id: str,
    ) -> tuple[ResourceClaim, ...]:
        safety = self._lineage_runtime_safety
        if safety is not None and self._state.is_custom_node(node_id):
            inherited = safety.links_for_node(node_id)
            if inherited:
                return inherited
        projection = self._real_projection
        if projection is not None:
            projected = projection.resources.get(node_id, ())
            if projected:
                return projected
        return ()

    def _node_context(self, node_id: str) -> dict[str, str]:
        projection = self._real_projection
        if projection is None:
            return {}
        return projection.entity_context.get(node_id, {})

from __future__ import annotations

from PySide6.QtCore import QTimer

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.atomic_lineage import build_real_lineage
from persona_training_lab.ui.agents.lineage import build_version_lineage
from persona_training_lab.ui.agents.real_lineage import RealLineageProjection
from persona_training_lab.ui.agents.runtime_policy import (
    LineageBranchTransactions,
    LineageRuntimePolicy,
)
from persona_training_lab.ui.agents.screen_agents_final import (
    AgentsScreen as _FinalAgentsScreen,
)
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


class AgentsScreen(_FinalAgentsScreen):
    """Final agents workspace backed by real persisted lineage and leases."""

    _RUNTIME_REFRESH_MS = 1_200

    def __init__(
        self,
        view_model,
        key_binding_manager: KeyBindingManager | None = None,
        lineage_runtime_safety: LineageRuntimeSafety | None = None,
    ) -> None:
        self._lineage_runtime_safety = lineage_runtime_safety
        self._runtime_policy = LineageRuntimePolicy(lineage_runtime_safety)
        self._branch_transactions = LineageBranchTransactions(
            lineage_runtime_safety
        )
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
            and node_id in projection.details
            and not self._state.is_custom_node(node_id)
        ):
            return projection.details[node_id]
        return super()._detail_for(node_id)

    def _continue_from_selected(self) -> None:
        parent_id = getattr(self, "_selected_node_id", "")
        fallback_claims = self._runtime_claims_for_node(parent_id)
        parent_is_custom = self._state.is_custom_node(parent_id)
        super()._continue_from_selected()
        child_id = getattr(self, "_selected_node_id", "")
        if not child_id:
            return
        self._branch_transactions.bind_child(
            child_id,
            parent_id,
            parent_is_custom=parent_is_custom,
            fallback_claims=fallback_claims,
        )
        self._refresh_runtime_safety(force=True)

    def _delete_local_branch_subtree(self, node_id: str) -> None:
        removed_ids = self._state.custom_subtree_ids(node_id)
        if not removed_ids:
            return
        blocker_state = self._runtime_policy.blockers_for(removed_ids)
        if blocker_state.blockers:
            self._show_runtime_blockers(blocker_state.blockers)
            return

        super()._delete_local_branch_subtree(node_id)
        if self._state.is_custom_node(node_id):
            # Confirmation was cancelled; dependency links stay untouched.
            return
        self._branch_transactions.forget(removed_ids)
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
        subtree_ids = (
            self._state.custom_subtree_ids(node_id)
            if is_custom
            else ()
        )
        overrides = self._runtime_policy.action_overrides(
            node_kind=context.get("node_kind", ""),
            is_custom=is_custom,
            is_current=is_current,
            is_archived=is_archived,
            subtree_ids=subtree_ids,
        )
        for button, enabled in (
            (self._make_current_action, overrides.make_current),
            (self._compare_action, overrides.compare),
            (self._portrait_action, overrides.portrait),
            (self._branch_action, overrides.branch),
            (self._delete_action, overrides.delete),
        ):
            if enabled is not None:
                button.setEnabled(enabled)

        if overrides.delete_reason_code == "registered_model_version":
            self._delete_action.setToolTip(
                "Зарегистрированные model versions удаляются только через "
                "отдельную транзакцию хранения, не из локального lineage."
            )
        elif overrides.delete_reason_code == "active_operation":
            self._delete_action.setToolTip(
                "Удаление временно заблокировано активной операцией: "
                + overrides.blocker_text
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
                    "evaluation_run": "Реальный тест / портрет",
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
        blocker_state = self._runtime_policy.blockers_for(node_ids)
        if (
            not force
            and blocker_state.signature == self._runtime_blocker_signature
        ):
            return
        self._runtime_blocker_signature = blocker_state.signature
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
        node_id = getattr(self, "_selected_node_id", "")
        if not node_id:
            return
        node_ids = (
            self._state.custom_subtree_ids(node_id)
            if self._state.is_custom_node(node_id)
            else (node_id,)
        )
        blocker_state = self._runtime_policy.blockers_for(node_ids)
        if blocker_state.blockers:
            base = self._detail_dependency.text().strip()
            runtime_text = (
                "Активная операция удерживает эту точку или её зависимость: "
                + blocker_state.text
                + ". Интерфейс остаётся доступен, но разрушительные действия "
                "временно отключены."
            )
            self._detail_dependency.setText(
                f"{base}\n\n{runtime_text}" if base else runtime_text
            )
            return

        links = self._runtime_policy.linked_resources(node_id)
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
        message = (
            "Удаление не выполнено: точка используется активной операцией. "
            + self._runtime_policy.text_for_blockers(blockers)
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
        return self._runtime_policy.blockers_for(node_ids).blockers

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
        projection = self._real_projection
        resources = {} if projection is None else projection.resources
        return self._runtime_policy.claims_for_node(
            node_id,
            is_custom=self._state.is_custom_node(node_id),
            projection_resources=resources,
        )

    def _node_context(self, node_id: str) -> dict[str, str]:
        projection = self._real_projection
        if projection is None:
            return {}
        return dict(projection.entity_context.get(node_id, {}))

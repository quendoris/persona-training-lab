from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import QPointF, QTimer
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.branch_deletion import (
    BranchDeletionCommittedError,
    BranchDeletionController,
    BranchDeletionResult,
    BranchDeletionStatus,
)
from persona_training_lab.ui.agents.context_navigation import (
    LineageContextRouter,
)
from persona_training_lab.ui.agents.lineage import build_version_lineage
from persona_training_lab.ui.agents.lineage_presentation import (
    LineagePresentationProjection,
)
from persona_training_lab.ui.agents.lineage_projection_adapter import (
    build_empty_lineage,
)
from persona_training_lab.ui.agents.lineage_projection_resolver import (
    build_lineage_projection,
)
from persona_training_lab.ui.agents.projection_runtime import (
    LineageRefreshIncidentReporter,
    ProjectionSafetyBinding,
)
from persona_training_lab.ui.agents.projection_updates import (
    ProjectionUpdateKind,
    ProjectionUpdatePlanner,
)
from persona_training_lab.ui.agents.refresh_coordinator import (
    LineageRefreshCoordinator,
)
from persona_training_lab.ui.agents.refresh_worker import (
    LineageRefreshFailure,
    LineageRefreshResult,
)
from persona_training_lab.ui.agents.runtime_policy import (
    LineageBranchTransactions,
    LineageRuntimePolicy,
)
from persona_training_lab.ui.agents.screen_workspace_presentation import (
    AgentsScreen as _WorkspacePresentationAgentsScreen,
)
from persona_training_lab.ui.agents.scroll_compensation import (
    ScrollPosition,
    WorkspaceScrollCompensator,
)
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import (
    make_muted_label,
    make_status_label,
)
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


_CONTEXT_ROUTER = LineageContextRouter()
_SCROLL_COMPENSATOR = WorkspaceScrollCompensator()


class AgentsScreen(_WorkspacePresentationAgentsScreen):
    """Compose the Agents workspace around an atomic lineage projection."""

    _RUNTIME_REFRESH_MS = 1_200

    def __init__(
        self,
        view_model,
        key_binding_manager: KeyBindingManager | None = None,
        lineage_runtime_safety: LineageRuntimeSafety | None = None,
        lineage_refresh_coordinator: LineageRefreshCoordinator | None = None,
    ) -> None:
        coordinator = lineage_refresh_coordinator
        owns_coordinator = False
        if coordinator is None:
            loader_factory = getattr(
                view_model,
                "lineage_loader_factory",
                None,
            )
            if loader_factory is not None:
                coordinator = LineageRefreshCoordinator(loader_factory)
                owns_coordinator = True

        self._lineage_refresh_coordinator = coordinator
        self._owns_lineage_refresh_coordinator = owns_coordinator
        self._lineage_runtime_safety = lineage_runtime_safety
        self._runtime_policy = LineageRuntimePolicy(lineage_runtime_safety)
        self._branch_transactions = LineageBranchTransactions(
            lineage_runtime_safety
        )
        self._runtime_blocker_signature: tuple[tuple[str, str, str], ...] = ()
        self._real_projection: LineagePresentationProjection | None = None
        self._real_projection_signature: tuple[
            tuple[str, str, str, str], ...
        ] = ()
        self._projection_safety_binding = ProjectionSafetyBinding(
            lineage_runtime_safety
        )
        self._refresh_incident_reporter = LineageRefreshIncidentReporter(
            getattr(view_model, "lineage_error_reporter", None)
        )
        self._projection_update_planner = ProjectionUpdatePlanner()

        try:
            super().__init__(view_model, key_binding_manager)
        except Exception:
            if owns_coordinator and coordinator is not None:
                coordinator.shutdown()
            raise

        self._branch_deletion_controller = BranchDeletionController(
            self._state,
            self._branch_transactions,
        )
        self._runtime_safety_timer = QTimer(self)
        self._runtime_safety_timer.setInterval(self._RUNTIME_REFRESH_MS)
        self._runtime_safety_timer.timeout.connect(
            self._refresh_runtime_safety
        )
        self._runtime_safety_timer.start()
        self._bind_projection_resources()
        self._refresh_runtime_safety(force=True)

        if coordinator is None:
            return
        if owns_coordinator:
            coordinator.setParent(self)
        self._runtime_safety_timer.stop()
        coordinator.projection_ready.connect(self._on_projection_ready)
        coordinator.refresh_failed.connect(self._on_projection_failed)
        last_good = coordinator.last_good
        if last_good is not None:
            self._on_projection_ready(last_good)

    def _build_nodes(self):
        coordinator = self._lineage_refresh_coordinator
        if coordinator is None:
            projection = build_lineage_projection(self._vm)
        else:
            result = coordinator.last_good
            projection = (
                result.projection if result is not None else build_empty_lineage()
            )
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

    def _open_workspace(self, workspace_key: str) -> None:
        selected_id = getattr(self, "_selected_node_id", "")
        current_id = self._state.current_node_id()
        if not current_id:
            current_id = self._graph.current_node_id()

        request = _CONTEXT_ROUTER.request(
            workspace_key,
            selected=self._context_for_node(selected_id),
            current=self._context_for_node(current_id),
        )
        window = self.window()
        contextual_navigator = getattr(
            window,
            "_go_to_screen_with_context",
            None,
        )
        if callable(contextual_navigator):
            contextual_navigator(
                request.workspace_key,
                request.mutable_payload(),
            )
            return
        super()._open_workspace(workspace_key)

    def _on_graph_zoom_anchor(
        self,
        anchor: QPointF,
        old_zoom: float,
        new_zoom: float,
    ) -> None:
        """Apply each pointer anchor immediately, without stale queued jumps."""

        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        target = _SCROLL_COMPENSATOR.zoom_target(
            ScrollPosition(hbar.value(), vbar.value()),
            anchor_x=anchor.x(),
            anchor_y=anchor.y(),
            old_zoom=old_zoom,
            new_zoom=new_zoom,
        )
        if target is None:
            return
        self._apply_workspace_scroll_shift(
            target.horizontal,
            target.vertical,
        )

    def _on_graph_workspace_origin_shift(self, delta: QPointF) -> None:
        """Compensate geometry growth synchronously during rapid gestures."""

        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        target = _SCROLL_COMPENSATOR.origin_shift_target(
            ScrollPosition(hbar.value(), vbar.value()),
            delta_x=delta.x(),
            delta_y=delta.y(),
        )
        self._apply_workspace_scroll_shift(
            target.horizontal,
            target.vertical,
        )

    def _delete_local_branch_subtree(self, node_id: str) -> None:
        if self._lineage_runtime_safety is None:
            super()._delete_local_branch_subtree(node_id)
            return

        node = self._node_by_id(node_id)
        if node is None:
            return
        plan = self._branch_deletion_controller.prepare(
            node_id,
            node_title=node.title,
            parent_id=node.parent_id or "",
            graph_current_id=self._graph.current_node_id(),
        )
        if plan is None:
            return

        detail = "Ветку можно будет вернуть через защищённую историю действий."
        if plan.descendant_count:
            detail = (
                "Будет удалена эта ветка и дочерние точки: "
                f"{plan.descendant_count}. "
                "Удаление сохранится в защищённой истории."
            )
        if not self._confirm_branch_deletion(plan.node_title, detail):
            return

        try:
            result = self._branch_deletion_controller.execute(
                plan,
                layout_snapshot=self._layout_snapshot(),
            )
        except BranchDeletionCommittedError as error:
            self._apply_branch_deletion_result(error.result)
            raise

        if result.status is BranchDeletionStatus.BLOCKED:
            self._show_runtime_blockers(result.blockers)
            return
        if result.status is BranchDeletionStatus.DELETED:
            self._apply_branch_deletion_result(result)
            return
        if result.status is BranchDeletionStatus.STALE:
            self._refresh_lineage(center=False)

    def _apply_branch_deletion_result(
        self,
        result: BranchDeletionResult,
    ) -> None:
        try:
            forgetter = getattr(self._graph, "forget_layout_nodes", None)
            if callable(forgetter):
                forgetter(result.removed_ids)
        finally:
            self._selected_node_id = result.fallback_id
            self._refresh_lineage(center=True)
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
        coordinator = self._lineage_refresh_coordinator
        if coordinator is None:
            if not self.isVisible() and not force:
                return
            projection = build_lineage_projection(self._vm)
            if force or projection.signature != self._real_projection_signature:
                self._apply_projection(projection)
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
        blocker_state = self._runtime_policy.blockers_for(node_ids)
        if (
            not force
            and blocker_state.signature == self._runtime_blocker_signature
        ):
            return
        self._runtime_blocker_signature = blocker_state.signature
        self._select_node(node_id)

    def _apply_projection(
        self,
        projection: LineagePresentationProjection,
    ) -> None:
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
        projection = self._real_projection
        if projection is None:
            return
        coordinator = self._lineage_refresh_coordinator
        snapshot_proven = (
            coordinator is None or coordinator.last_good is not None
        )
        self._projection_safety_binding.reconcile(
            projection.resources,
            snapshot_proven=snapshot_proven,
        )

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

    def _context_for_node(self, node_id: str) -> dict[str, str]:
        node = self._node_by_id(node_id) if node_id else None
        context = _CONTEXT_ROUTER.node_context(
            node_id,
            base_context=self._node_context(node_id),
            node_title="" if node is None else node.title,
            node_status="" if node is None else node.status,
            claims=self._runtime_claims_for_node(node_id),
        )
        return dict(context)

    def _roles(self) -> QWidget:
        if self._lineage_refresh_coordinator is None:
            return super()._roles()
        content = QWidget()
        content.setProperty("transparentBg", True)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        card = PanelCard(
            "Рабочие роли",
            "Подсказки рассчитаны из того же атомарного lineage snapshot.",
        )
        self._projection_roles_layout = QVBoxLayout()
        self._projection_roles_layout.setSpacing(8)
        card._layout.addLayout(self._projection_roles_layout)
        layout.addWidget(card)
        layout.addStretch(1)
        self._roles_content = content
        self._refresh_projection_roles()
        return self._bounded_column_scroll(
            content,
            object_name="AgentsRolesScroll",
            minimum_width=self._ROLES_MIN_WIDTH,
            maximum_width=self._ROLES_MAX_WIDTH,
        )

    def _refresh_projection_roles(self) -> None:
        layout = getattr(self, "_projection_roles_layout", None)
        if layout is None:
            return
        self._clear_layout(layout)
        for title, mission, next_action, status in self._projection_roles():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            title_label = QLabel(title)
            title_label.setObjectName("CardTitle")
            row_layout.addWidget(title_label)
            row_layout.addWidget(make_muted_label(mission))
            row_layout.addWidget(make_muted_label(next_action))
            row_layout.addWidget(make_status_label(status, "pending"))
            layout.addWidget(row)

    def _projection_roles(
        self,
    ) -> tuple[tuple[str, str, str, str], ...]:
        projection = self._real_projection
        if projection is None:
            return ()
        contexts = projection.entity_context
        real_contexts = tuple(
            context
            for context in contexts.values()
            if not self._is_placeholder_context(context)
        )
        dataset_count = sum(
            context.get("node_kind") == "dataset"
            for context in real_contexts
        )
        evaluation_count = sum(
            context.get("node_kind") == "evaluation_run"
            for context in real_contexts
        )
        bad_count = sum(node.tone == "bad" for node in projection.nodes)
        pending_count = sum(
            node.tone == "pending"
            and not self._is_placeholder_context(
                contexts.get(node.node_id, {})
            )
            for node in projection.nodes
        )
        unresolved_count = sum(
            "unresolved:" in node.subtitle
            for node in projection.nodes
        )
        snapshot_context = contexts.get("snapshot", {})
        current_version = snapshot_context.get("model_version_id", "")
        delta_context = contexts.get("delta", {})
        delta_ready = bool(
            delta_context.get("left_experiment_id")
            and delta_context.get("right_experiment_id")
        )
        next_action = self._projection_next_action(contexts, delta_ready)
        return (
            (
                "Версионный навигатор",
                "Следит за причинной цепочкой model lineage.",
                next_action,
                "главный",
            ),
            (
                "Исследователь",
                "Сверяет реальные evaluation runs и delta.",
                f"Портретов: {evaluation_count}; delta: "
                + ("готова" if delta_ready else "нужен второй запуск"),
                "анализ",
            ),
            (
                "Аудитор датасета",
                "Проверяет состояние данных до продолжения обучения.",
                f"Датасетов: {dataset_count}; проблемных узлов: {bad_count}.",
                "проверка",
            ),
            (
                "Протоколист",
                "Не позволяет скрыть разорванные зависимости.",
                f"Unresolved связей: {unresolved_count}; current: "
                f"{current_version or '—'}.",
                "протокол",
            ),
            (
                "Разметчик",
                "Готовит corrective data по неустойчивым результатам.",
                f"Ожидающих или partial узлов: {pending_count}.",
                "позже",
            ),
        )

    @staticmethod
    def _is_placeholder_context(context: Mapping[str, str]) -> bool:
        return context.get("node_kind", "").endswith("_placeholder")

    @classmethod
    def _projection_next_action(
        cls,
        contexts: Mapping[str, Mapping[str, str]],
        delta_ready: bool,
    ) -> str:
        for node_id, action in (
            ("dataset", "Добавьте и проверьте датасет."),
            ("training", "Создайте и завершите training run."),
            ("snapshot", "Зарегистрируйте model version из artifact."),
            ("portrait", "Соберите портрет текущей model version."),
        ):
            if cls._is_placeholder_context(contexts.get(node_id, {})):
                return action
        if not delta_ready:
            return "Соберите второй сопоставимый portrait для delta."
        return "Откройте анализ и проверьте следующую ветку."

    def request_projection_refresh(self, *, force: bool = True) -> None:
        coordinator = self._lineage_refresh_coordinator
        if coordinator is not None:
            coordinator.request_refresh(force=force)

    def shutdown_background_work(self, timeout_ms: int = 6_500) -> bool:
        coordinator = self._lineage_refresh_coordinator
        if coordinator is None:
            return True
        return coordinator.shutdown(timeout_ms)

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
        plan = self._projection_update_planner.plan(result.revisions)
        if plan is ProjectionUpdateKind.NOOP:
            self._refresh_runtime_blockers(force=False)
            return
        if plan is ProjectionUpdateKind.FULL:
            self._apply_projection(result.projection)
        elif not self._apply_projection_content(result):
            self._apply_projection(result.projection)

        self._projection_update_planner.commit(result.revisions)
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

    def _on_projection_failed(self, failure: LineageRefreshFailure) -> None:
        coordinator = self._lineage_refresh_coordinator
        last_good_available = (
            coordinator is not None and coordinator.last_good is not None
        )
        correlation = self._refresh_incident_reporter.report(
            failure,
            last_good_available=last_good_available,
        )
        window = self.window()
        status = getattr(window, "_status", None)
        setter = getattr(status, "set_message", None)
        if not callable(setter):
            return
        if correlation:
            setter(
                "Lineage refresh не обновлён; сохранён последний "
                f"согласованный снимок. Код события: {correlation}."
            )
            return
        setter(
            "Lineage refresh не обновлён; сохранён последний "
            f"согласованный снимок ({failure.error_type})."
        )

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import QPointF, QTimer
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.messages import UserMessage
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
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.viewmodels.agents_contracts import AgentDetailView


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
        localization: LocalizationManager | None = None,
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
        self._runtime_blocker_signature: tuple[
            tuple[str, str, str], ...
        ] = ()
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
            super().__init__(
                view_model,
                key_binding_manager,
                localization,
            )
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

        if coordinator is not None:
            if owns_coordinator:
                coordinator.setParent(self)
            self._runtime_safety_timer.stop()
            coordinator.projection_ready.connect(self._on_projection_ready)
            coordinator.refresh_failed.connect(self._on_projection_failed)
            last_good = coordinator.last_good
            if last_good is not None:
                self._on_projection_ready(last_good)

        if localization is not None:
            localization.language_changed.connect(
                self._refresh_language
            )

    def _build_nodes(self):
        coordinator = self._lineage_refresh_coordinator
        if coordinator is None:
            projection = build_lineage_projection(self._vm)
        else:
            result = coordinator.last_good
            projection = (
                result.projection
                if result is not None
                else build_empty_lineage()
            )
        self._real_projection = projection
        self._real_projection_signature = projection.signature
        return self._state.apply(
            build_version_lineage(projection.nodes)
        )

    def _detail_for(self, node_id: str) -> AgentDetailView:
        projection = self._real_projection
        if (
            projection is not None
            and node_id in projection.details
            and not self._state.is_custom_node(node_id)
        ):
            detail = projection.details[node_id]
            return self._with_key_binding_help(
                AgentDetailView(
                    title=detail.title,
                    body=detail.body,
                    checks=detail.checks,
                    actions=detail.actions,
                    action_codes=(
                        *detail.action_codes,
                        "open_actions",
                        "pan",
                        "toggle",
                        "undo",
                    ),
                )
            )
        node = self._node_by_id(node_id)
        if node is not None and self._state.is_custom_node(node_id):
            return super()._detail_for(node_id)
        return self._with_key_binding_help(
            AgentDetailView(
                title=UserMessage("agents.node.kind.unknown"),
                body=UserMessage("agents.detail.unknown.body"),
                checks=(
                    UserMessage("agents.detail.unknown.check.snapshot"),
                    UserMessage("agents.detail.unknown.check.refresh"),
                ),
                actions=(),
                action_codes=(
                    "open_actions",
                    "pan",
                    "toggle",
                    "undo",
                ),
            )
        )

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
            node_title=self._render_text(node.title),
            parent_id=node.parent_id or "",
            graph_current_id=self._graph.current_node_id(),
        )
        if plan is None:
            return

        detail = self._text("agents.dialog.delete.single")
        if plan.descendant_count:
            detail = self._text(
                "agents.dialog.delete.subtree",
                count=plan.descendant_count,
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
                self._text("agents.runtime.delete_registered")
            )
        elif overrides.delete_reason_code == "active_operation":
            self._delete_action.setToolTip(
                self._text(
                    "agents.runtime.delete_active",
                    blocker=overrides.blocker_text,
                )
            )

    def _render_detail(self, detail: AgentDetailView) -> None:
        super()._render_detail(detail)
        context = self._node_context(
            getattr(self, "_selected_node_id", "")
        )
        kind = context.get("node_kind", "")
        if kind:
            key = {
                "base_model": "agents.node.kind.base_model",
                "dataset": "agents.node.kind.dataset",
                "training_run": "agents.node.kind.training_run",
                "model_version": "agents.node.kind.model_version",
                "experiment": "agents.node.kind.evaluation_run",
                "evaluation_run": "agents.node.kind.evaluation_run",
                "analysis_delta": "agents.node.kind.analysis_delta",
            }.get(kind)
            if key is not None:
                self._detail_type_value.setText(self._text(key))
        self._apply_runtime_dependency_text()

    def _refresh_runtime_safety(self, *, force: bool = False) -> None:
        coordinator = self._lineage_refresh_coordinator
        if coordinator is None:
            if not self.isVisible() and not force:
                return
            projection = build_lineage_projection(self._vm)
            if (
                force
                or projection.signature
                != self._real_projection_signature
            ):
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
            and blocker_state.signature
            == self._runtime_blocker_signature
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
        base = self._detail_dependency.text().strip()
        if blocker_state.blockers:
            runtime_text = self._text(
                "agents.runtime.blocker_detail",
                blocker=blocker_state.text,
            )
            self._detail_dependency.setText(
                f"{base}\n\n{runtime_text}" if base else runtime_text
            )
            return

        links = self._runtime_policy.linked_resources(node_id)
        if links:
            linked = ", ".join(
                f"{claim.resource_kind}={claim.resource_id}"
                for claim in links
            )
            runtime_text = self._text(
                "agents.runtime.linked_resources",
                resources=linked,
            )
            self._detail_dependency.setText(
                f"{base}\n\n{runtime_text}" if base else runtime_text
            )

    def _show_runtime_blockers(self, blockers) -> None:
        blocker_text = self._runtime_policy.text_for_blockers(blockers)
        message = self._text(
            "agents.runtime.delete_blocked",
            blockers=blocker_text,
        )
        self._detail_dependency.setText(message)
        self._delete_action.setEnabled(False)
        self._delete_action.setToolTip(message)
        self._set_window_status_message(
            "agents.runtime.delete_blocked",
            blockers=blocker_text,
        )

    def _set_window_status_message(
        self,
        key: str,
        **values: object,
    ) -> None:
        window = self.window()
        status = getattr(window, "_status", None)
        semantic_setter = getattr(status, "set_message_key", None)
        if callable(semantic_setter):
            semantic_setter(key, **values)
            return
        setter = getattr(status, "set_message", None)
        if callable(setter):
            setter(self._text(key, **values))

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
        resources = (
            {} if projection is None else projection.resources
        )
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
            node_title=(
                "" if node is None else self._render_text(node.title)
            ),
            node_status=(
                "" if node is None else self._render_text(node.status)
            ),
            claims=self._runtime_claims_for_node(node_id),
        )
        return dict(context)

    def _roles(self) -> QWidget:
        content = QWidget()
        content.setProperty("transparentBg", True)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        card = PanelCard(
            self._text("agents.roles.title"),
            self._text("agents.roles.projection_subtitle"),
        )
        self._roles_card = card
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
            row_layout.addWidget(
                make_status_label(status, "pending")
            )
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
        bad_count = sum(
            node.tone == "bad" for node in projection.nodes
        )
        pending_count = sum(
            node.tone == "pending"
            and not self._is_placeholder_context(
                contexts.get(node.node_id, {})
            )
            for node in projection.nodes
        )
        unresolved_count = self._projection_unresolved_count(projection)
        snapshot_context = contexts.get("snapshot", {})
        current_version = snapshot_context.get("model_version_id", "")
        delta_context = contexts.get("delta", {})
        delta_ready = bool(
            delta_context.get("left_experiment_id")
            and delta_context.get("right_experiment_id")
        )
        next_action = self._projection_next_action(
            contexts,
            delta_ready,
        )
        delta_text = self._text(
            "agents.role.researcher.delta_ready"
            if delta_ready
            else "agents.role.researcher.delta_pending"
        )
        return (
            (
                self._text("agents.role.navigator.title"),
                self._text("agents.role.navigator.mission"),
                next_action,
                self._text("agents.role.navigator.status"),
            ),
            (
                self._text("agents.role.researcher.title"),
                self._text("agents.role.researcher.mission"),
                self._text(
                    "agents.role.researcher.next",
                    count=evaluation_count,
                    delta=delta_text,
                ),
                self._text("agents.role.researcher.status"),
            ),
            (
                self._text("agents.role.dataset.title"),
                self._text("agents.role.dataset.mission"),
                self._text(
                    "agents.role.dataset.next",
                    datasets=dataset_count,
                    bad=bad_count,
                ),
                self._text("agents.role.dataset.status"),
            ),
            (
                self._text("agents.role.protocol.title"),
                self._text("agents.role.protocol.mission"),
                self._text(
                    "agents.role.protocol.next",
                    unresolved=unresolved_count,
                    current=current_version or "—",
                ),
                self._text("agents.role.protocol.status"),
            ),
            (
                self._text("agents.role.labeler.title"),
                self._text("agents.role.labeler.mission"),
                self._text(
                    "agents.role.labeler.next",
                    pending=pending_count,
                ),
                self._text("agents.role.labeler.status"),
            ),
        )

    @staticmethod
    def _projection_unresolved_count(
        projection: LineagePresentationProjection,
    ) -> int:
        count = 0
        for detail in projection.details.values():
            body = detail.body
            if not isinstance(body, UserMessage):
                continue
            if body.key != "agents.detail.semantic_body":
                continue
            unresolved = str(body.values.get("unresolved", "—"))
            if unresolved and unresolved != "—":
                count += len(unresolved.splitlines())
        return count

    @staticmethod
    def _is_placeholder_context(context: Mapping[str, str]) -> bool:
        return context.get("node_kind", "").endswith("_placeholder")

    def _projection_next_action(
        self,
        contexts: Mapping[str, Mapping[str, str]],
        delta_ready: bool,
    ) -> str:
        for node_id, key in (
            ("dataset", "agents.next.dataset"),
            ("training", "agents.next.training"),
            ("snapshot", "agents.next.snapshot"),
            ("portrait", "agents.next.portrait"),
        ):
            if self._is_placeholder_context(
                contexts.get(node_id, {})
            ):
                return self._text(key)
        if not delta_ready:
            return self._text("agents.next.delta")
        return self._text("agents.next.analysis")

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
        if correlation:
            self._set_window_status_message(
                "agents.refresh.failed_with_code",
                correlation=correlation,
            )
            return
        self._set_window_status_message(
            "agents.refresh.failed",
            error_type=failure.error_type,
        )

    def _refresh_language(self, _locale: str = "") -> None:
        """Refresh presentation only; never rebuild or persist lineage state."""

        before_signature = self._real_projection_signature
        selected = getattr(self, "_selected_node_id", "")
        self._refresh_presentation_language()
        self._refresh_projection_roles()
        if selected:
            self._selected_node_id = selected
        if self._real_projection_signature != before_signature:
            raise RuntimeError(
                "Localization refresh must not replace lineage projection"
            )

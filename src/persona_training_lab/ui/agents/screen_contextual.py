from __future__ import annotations

from PySide6.QtCore import QPointF

from persona_training_lab.ui.agents.branch_deletion import (
    BranchDeletionCommittedError,
    BranchDeletionController,
    BranchDeletionResult,
    BranchDeletionStatus,
)
from persona_training_lab.ui.agents.context_navigation import (
    LineageContextRouter,
)
from persona_training_lab.ui.agents.screen_background import (
    AgentsScreen as _BackgroundAgentsScreen,
)
from persona_training_lab.ui.agents.scroll_compensation import (
    ScrollPosition,
    WorkspaceScrollCompensator,
)


_CONTEXT_ROUTER = LineageContextRouter()
_SCROLL_COMPENSATOR = WorkspaceScrollCompensator()


class AgentsScreen(_BackgroundAgentsScreen):
    """Lineage workspace with contextual routing and atomic branch deletion."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._branch_deletion_controller = BranchDeletionController(
            self._state,
            self._branch_transactions,
        )

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
        if getattr(self, "_lineage_runtime_safety", None) is None:
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

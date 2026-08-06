from __future__ import annotations

from PySide6.QtCore import QPointF

from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
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
        transactions = getattr(self, "_branch_transactions", None)
        if (
            getattr(self, "_lineage_runtime_safety", None) is None
            or transactions is None
        ):
            super()._delete_local_branch_subtree(node_id)
            return

        node = self._node_by_id(node_id)
        removed_ids = self._state.custom_subtree_ids(node_id)
        if node is None or not removed_ids:
            return
        descendants = len(removed_ids) - 1
        detail = (
            "Ветку можно будет вернуть через защищённую историю действий."
        )
        if descendants:
            detail = (
                "Будет удалена эта ветка и дочерние точки: "
                f"{descendants}. Удаление сохранится в защищённой истории."
            )
        if not self._confirm_branch_deletion(node.title, detail):
            return

        try:
            lease = transactions.begin_deletion(
                removed_ids,
                subject_id=node_id,
            )
        except OperationConflictError as conflict:
            self._show_runtime_blockers(conflict.blockers)
            return
        if lease is None:
            return

        try:
            fallback_id = node.parent_id or self._graph.current_node_id()
            removed = self._state.delete_subtree(
                node_id,
                self._layout_snapshot(),
            )
            if not removed:
                lease.cancel("Ветка не была удалена")
                return
            if hasattr(self._graph, "forget_layout_nodes"):
                self._graph.forget_layout_nodes(removed)
            transactions.forget(removed)
            self._selected_node_id = fallback_id
            lease.succeed()
            self._refresh_lineage(center=True)
        except Exception as error:
            lease.fail(str(error))
            raise

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

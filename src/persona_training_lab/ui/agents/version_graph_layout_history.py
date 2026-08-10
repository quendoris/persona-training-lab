from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QMouseEvent

from persona_training_lab.ui.agents.drag_scope import (
    drag_history_action_code,
    drag_target_ids,
)
from persona_training_lab.ui.agents.version_graph_layout_authority import (
    VersionGraphCanvas as LayoutAuthorityVersionGraphCanvas,
)


class VersionGraphCanvas(LayoutAuthorityVersionGraphCanvas):
    """Own layout snapshots and history transactions for graph mutations."""

    layout_action_committed = Signal(str, object, bool)

    def __init__(self, nodes) -> None:
        self._drag_history_before: dict[str, Any] | None = None
        self._drag_history_moved_node = False
        self._drag_history_moved_subtree = False
        super().__init__(nodes)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_history_before = None
        self._drag_history_moved_node = False
        self._drag_history_moved_subtree = False
        if (
            event.button() == Qt.MouseButton.RightButton
            and not self.layout_locked()
        ):
            node_id = self._node_at(event.position())
            if node_id is not None:
                self._drag_history_before = self.layout_snapshot()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        node_id = getattr(self, "_drag_node_id", None)
        drag_mode = getattr(self, "_drag_mode", None)
        is_node_drag = (
            node_id is not None
            and drag_mode in {"node", "subtree"}
            and bool(event.buttons() & Qt.MouseButton.RightButton)
        )
        scope_is_subtree = False
        before_move: dict[str, Any] | None = None
        if is_node_drag:
            scope_is_subtree = bool(
                event.modifiers()
                & Qt.KeyboardModifier.ShiftModifier
            )
            subtree_ids = self._subtree_node_ids(node_id)
            self._drag_mode = (
                "subtree" if scope_is_subtree else "node"
            )
            self._drag_target_ids = drag_target_ids(
                node_id,
                subtree_ids,
                shift_down=scope_is_subtree,
            )
            before_move = self.layout_snapshot()

        super().mouseMoveEvent(event)

        if (
            before_move is not None
            and before_move != self.layout_snapshot()
        ):
            if scope_is_subtree:
                self._drag_history_moved_subtree = True
            else:
                self._drag_history_moved_node = True

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        before = self._drag_history_before
        moved_node = self._drag_history_moved_node
        moved_subtree = self._drag_history_moved_subtree
        super().mouseReleaseEvent(event)
        self._drag_history_before = None
        self._drag_history_moved_node = False
        self._drag_history_moved_subtree = False
        if before is not None and before != self.layout_snapshot():
            action_code = drag_history_action_code(
                moved_node=moved_node,
                moved_subtree=moved_subtree,
            )
            self.layout_action_committed.emit(
                action_code,
                before,
                False,
            )

    def layout_snapshot(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "offsets": {
                node_id: {"x": point.x(), "y": point.y()}
                for node_id, point in sorted(
                    self._node_offsets.items()
                )
                if point.x() or point.y()
            },
        }

    def restore_layout_snapshot(
        self,
        snapshot: dict[str, Any],
    ) -> None:
        if not isinstance(snapshot, dict) or "offsets" not in snapshot:
            return
        raw_offsets = snapshot.get("offsets", {})
        if not isinstance(raw_offsets, dict):
            return
        known_ids = {node.node_id for node in self._nodes}
        restored: dict[str, QPointF] = {}
        for node_id, raw in raw_offsets.items():
            if node_id not in known_ids or not isinstance(raw, dict):
                continue
            try:
                point = QPointF(
                    float(raw.get("x", 0.0)),
                    float(raw.get("y", 0.0)),
                )
            except (TypeError, ValueError):
                continue
            if point.x() or point.y():
                restored[node_id] = point
        self._node_offsets = restored
        self._layout_dirty = False
        self._save_offsets()
        self.update()

    def reset_layout(self) -> None:
        before = self.layout_snapshot()
        super().reset_layout()
        if before != self.layout_snapshot():
            self.layout_action_committed.emit(
                "layout_reset_all",
                before,
                True,
            )

    def reset_node_layout(self, node_id: str) -> None:
        before = self.layout_snapshot()
        super().reset_node_layout(node_id)
        if before != self.layout_snapshot():
            self.layout_action_committed.emit(
                "layout_reset_node",
                before,
                False,
            )

    def reset_subtree_layout(self, node_id: str) -> None:
        before = self.layout_snapshot()
        super().reset_subtree_layout(node_id)
        if before != self.layout_snapshot():
            self.layout_action_committed.emit(
                "layout_reset_subtree",
                before,
                False,
            )

    def forget_layout_nodes(
        self,
        node_ids: Iterable[str],
    ) -> None:
        removed = set(node_ids)
        for node_id in removed:
            self._node_offsets.pop(node_id, None)
        if getattr(self, "_menu_node_id", None) in removed:
            self._menu_node_id = None
        if removed:
            self._save_offsets()
            self.update()

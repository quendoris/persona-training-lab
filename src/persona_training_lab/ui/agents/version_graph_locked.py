from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent

from persona_training_lab.ui.agents.version_graph_persistent import VersionGraphCanvas as PersistentVersionGraphCanvas


class VersionGraphCanvas(PersistentVersionGraphCanvas):
    def __init__(self, nodes) -> None:
        super().__init__(nodes)
        self._layout_locked = self._load_layout_locked()

    def layout_locked(self) -> bool:
        return self._layout_locked

    def set_layout_locked(self, locked: bool) -> None:
        self._layout_locked = locked
        self._save_offsets()
        self.update()

    def toggle_flipped(self) -> None:
        self._flipped = not self._flipped
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self._press_global_pos = event.globalPosition()
            self._last_global_pos = event.globalPosition()
            self._dragging = False
            self._drag_mode = "right_pan"
            self._drag_node_id = None
            self._drag_target_ids = ()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() != Qt.MouseButton.LeftButton or not self._layout_locked:
            super().mousePressEvent(event)
            return

        node_id = self._node_at(event.position())
        if node_id is None:
            super().mousePressEvent(event)
            return

        self._press_global_pos = event.globalPosition()
        self._last_global_pos = event.globalPosition()
        self._dragging = False
        self._drag_mode = "locked_node"
        self._drag_node_id = node_id
        self._drag_target_ids = ()
        self._selected_node_id = node_id
        self.node_selected.emit(node_id)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_mode == "right_pan":
            if self._press_global_pos is None or self._last_global_pos is None or not event.buttons() & Qt.MouseButton.RightButton:
                super().mouseMoveEvent(event)
                return
            current = event.globalPosition()
            delta = current - self._last_global_pos
            total = current - self._press_global_pos
            if self._dragging or abs(total.x()) + abs(total.y()) > 2:
                self._dragging = True
                self._last_global_pos = current
                if delta.x() or delta.y():
                    self.pan_requested.emit(delta)
            event.accept()
            return
        if self._drag_mode == "locked_node":
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton and self._drag_mode == "right_pan":
            self.unsetCursor()
            self._press_global_pos = None
            self._last_global_pos = None
            self._dragging = False
            self._drag_mode = None
            self._drag_node_id = None
            self._drag_target_ids = ()
            event.accept()
            return
        if self._drag_mode != "locked_node":
            super().mouseReleaseEvent(event)
            return
        self.unsetCursor()
        self._press_global_pos = None
        self._last_global_pos = None
        self._dragging = False
        self._drag_mode = None
        self._drag_node_id = None
        self._drag_target_ids = ()
        event.accept()

    def _positions(self) -> dict[str, tuple[float, float]]:
        lanes = self._lanes()
        max_level = self._max_level()
        row_gap = 52 * self._zoom
        branch_gap = 104 * self._zoom
        axis_x = 1050 * self._zoom
        top = 738 * self._zoom
        result: dict[str, tuple[float, float]] = {}
        for node in self._nodes:
            level = self._display_level(node)
            visual_level = max_level - level if self._flipped else level
            offset = self._node_offsets.get(node.node_id, QPointF())
            offset_y = -offset.y() if self._flipped else offset.y()
            result[node.node_id] = (
                axis_x + lanes.get(node.node_id, 0) * branch_gap + offset.x() * self._zoom,
                top + visual_level * row_gap + offset_y * self._zoom,
            )
        return result

    def _max_level(self) -> int:
        return max((self._display_level(node) for node in self._nodes), default=0)

    def _display_level(self, node) -> int:
        return self._level(node) + self._mainline_extra_slots(node.node_id)

    def _mainline_extra_slots(self, node_id: str) -> int:
        by_id = {node.node_id: node for node in self._nodes}
        if node_id not in by_id or self._has_side_ancestor_or_self(node_id, by_id):
            return 0
        children_by_id = self._children_by_id()
        extra = 0
        current_id = node_id
        while current_id in by_id:
            parent_id = self._parent(by_id[current_id])
            if parent_id is None or parent_id not in by_id:
                break
            side_siblings = [child_id for child_id in children_by_id.get(parent_id, ()) if child_id in by_id and self._side(by_id[child_id])]
            if side_siblings:
                extra += len(side_siblings)
            current_id = parent_id
        return extra

    def _has_side_ancestor_or_self(self, node_id: str, by_id: dict[str, object]) -> bool:
        current_id: str | None = node_id
        while current_id is not None and current_id in by_id:
            node = by_id[current_id]
            if self._side(node):
                return True
            current_id = self._parent(node)
        return False

    def _move_nodes(self, node_ids: tuple[str, ...], delta: QPointF) -> None:
        if self._layout_locked or not node_ids or not (delta.x() or delta.y()):
            return
        layout_delta = QPointF(delta.x() / self._zoom, delta.y() / self._zoom)
        if self._flipped:
            layout_delta.setY(-layout_delta.y())
        for node_id in node_ids:
            current = self._node_offsets.get(node_id, QPointF())
            self._node_offsets[node_id] = QPointF(current.x() + layout_delta.x(), current.y() + layout_delta.y())
        self._layout_dirty = True
        self.update()

    def _load_layout_locked(self) -> bool:
        try:
            payload = json.loads(self._layout_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        return bool(payload.get("layout_locked", False))

    def _save_offsets(self) -> None:
        try:
            self._layout_path.parent.mkdir(parents=True, exist_ok=True)
            payload: dict[str, Any] = {
                "schema": 2,
                "layout_locked": self._layout_locked,
                "offsets": {
                    node_id: {"x": point.x(), "y": point.y()}
                    for node_id, point in sorted(self._node_offsets.items())
                    if point.x() or point.y()
                },
            }
            self._layout_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            return

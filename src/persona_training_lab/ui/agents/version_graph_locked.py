from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
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
        if self._drag_mode == "locked_node":
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
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
        branch_gap = 84 * self._zoom
        axis_x = 1050 * self._zoom
        top = 738 * self._zoom
        result: dict[str, tuple[float, float]] = {}
        for node in self._nodes:
            level = self._level(node)
            visual_level = max_level - level if self._flipped else level
            offset = self._node_offsets.get(node.node_id, QPointF())
            offset_y = -offset.y() if self._flipped else offset.y()
            result[node.node_id] = (
                axis_x + lanes.get(node.node_id, 0) * branch_gap + offset.x() * self._zoom,
                top + visual_level * row_gap + offset_y * self._zoom,
            )
        return result

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

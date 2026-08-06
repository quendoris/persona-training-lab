from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFontMetricsF, QMouseEvent

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
        lane_offsets = self._lane_offsets(lanes)
        levels = self._display_levels()
        max_level = max(levels.values(), default=0)
        row_gap = 52 * self._zoom
        axis_x = 1050 * self._zoom
        top = 738 * self._zoom
        result: dict[str, tuple[float, float]] = {}
        for node in self._nodes:
            level = levels.get(node.node_id, self._level(node))
            visual_level = max_level - level if self._flipped else level
            offset = self._node_offsets.get(node.node_id, QPointF())
            offset_y = -offset.y() if self._flipped else offset.y()
            lane_offset = lane_offsets.get(lanes.get(node.node_id, 0), 0.0)
            result[node.node_id] = (
                axis_x + lane_offset * self._zoom + offset.x() * self._zoom,
                top + visual_level * row_gap + offset_y * self._zoom,
            )
        return result

    def _max_level(self) -> int:
        return max(self._display_levels().values(), default=0)

    def _display_levels(self) -> dict[str, int]:
        children = self._children_by_id()
        by_id = {node.node_id: node for node in self._nodes}
        levels: dict[str, int] = {}

        def assign(node_id: str, level: int) -> None:
            if node_id in levels:
                return
            levels[node_id] = level
            node_children = [child_id for child_id in children.get(node_id, []) if child_id in by_id]
            side_children = [child_id for child_id in node_children if self._side(by_id[child_id])]
            main_children = [child_id for child_id in node_children if not self._side(by_id[child_id])]
            side_slot = level + 1
            for offset, child_id in enumerate(side_children):
                assign(child_id, side_slot + offset)
            main_slot = level + 1 + len(side_children)
            for child_id in main_children:
                assign(child_id, main_slot)

        for root in children.get(None, []):
            assign(root, 0)
        for node in self._nodes:
            if node.node_id not in levels:
                parent_id = self._parent(node)
                if parent_id in levels:
                    assign(node.node_id, levels[parent_id] + 1)
                else:
                    assign(node.node_id, self._level(node))
        return levels

    def _lanes(self) -> dict[str, int]:
        children: dict[str | None, list[object]] = {}
        for node in self._nodes:
            children.setdefault(self._parent(node), []).append(node)
        lanes: dict[str, int] = {}

        def assign(node, lane: int) -> None:
            lanes[node.node_id] = lane
            node_children = children.get(node.node_id, [])
            main = [child for child in node_children if not self._side(child)]
            side = [child for child in node_children if self._side(child)]
            for child in main:
                assign(child, lane)
            for index, child in enumerate(side):
                if self._side(node):
                    next_lane = lane
                else:
                    next_lane = self._side_lane(lane, index)
                assign(child, next_lane)

        for root in children.get(None, []):
            assign(root, 0)
        return lanes

    def _side_lane(self, parent_lane: int, index: int) -> int:
        step = index // 2 + 1
        direction = 1 if index % 2 == 0 else -1
        return parent_lane + direction * step

    def _lane_offsets(self, lanes: dict[str, int]) -> dict[int, float]:
        by_id = {node.node_id: node for node in self._nodes}
        lane_ids = sorted(set(lanes.values()))
        min_right: dict[int, float] = {}
        min_left: dict[int, float] = {}
        for node in self._nodes:
            lane = lanes.get(node.node_id, 0)
            if lane == 0:
                continue
            parent_id = self._parent(node)
            parent = by_id.get(parent_id) if parent_id is not None else None
            child_width = self._label_width(node.title)
            parent_width = self._label_width(parent.title) if parent is not None and not self._side(parent) else 0.0
            if lane > 0:
                min_right[lane] = max(min_right.get(lane, 104.0 * lane), parent_width + 86.0, 104.0 * lane)
            else:
                min_left[lane] = max(min_left.get(lane, 104.0 * abs(lane)), child_width + 64.0, 104.0 * abs(lane))

        offsets: dict[int, float] = {0: 0.0}
        previous = 0.0
        for lane in [item for item in lane_ids if item > 0]:
            previous = max(previous + 112.0, min_right.get(lane, 104.0 * lane))
            offsets[lane] = previous
        previous = 0.0
        for lane in sorted((item for item in lane_ids if item < 0), reverse=True):
            previous = max(previous + 112.0, min_left.get(lane, 104.0 * abs(lane)))
            offsets[lane] = -previous
        return offsets

    def _label_width(self, title: str) -> float:
        try:
            return float(QFontMetricsF(self.font()).horizontalAdvance(self._display_label(title)))
        except Exception:
            return float(len(self._display_label(title)) * 7)

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

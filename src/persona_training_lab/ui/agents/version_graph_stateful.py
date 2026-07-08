from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QMouseEvent

from persona_training_lab.ui.agents.version_graph_locked import VersionGraphCanvas as LockableVersionGraphCanvas
from persona_training_lab.ui.viewmodels.agents import VersionNodeView


class VersionGraphCanvas(LockableVersionGraphCanvas):
    context_menu_requested = Signal(str, QPointF)
    context_menu_dismiss_requested = Signal()

    def set_nodes(self, nodes: tuple[VersionNodeView, ...]) -> None:
        self._nodes = nodes
        ids = {node.node_id for node in nodes}
        if self._selected_node_id not in ids:
            self._selected_node_id = self.current_node_id()
        self._hit_rects.clear()
        self._refresh_size()
        self.updateGeometry()
        self.update()

    def reset_node_layout(self, node_id: str) -> None:
        self._node_offsets.pop(node_id, None)
        self._save_offsets()
        self.update()

    def reset_subtree_layout(self, node_id: str) -> None:
        for target_id in self._subtree_node_ids(node_id):
            self._node_offsets.pop(target_id, None)
        self._save_offsets()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            node_id = self._node_at(event.position())
            if node_id is None:
                self.context_menu_dismiss_requested.emit()
            else:
                self._selected_node_id = node_id
                self.update()
                self.node_selected.emit(node_id)
                self.context_menu_requested.emit(node_id, event.globalPosition())
            event.accept()
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.context_menu_dismiss_requested.emit()
            node_id = self._node_at(event.position())
            self._press_global_pos = event.globalPosition()
            self._last_global_pos = event.globalPosition()
            self._dragging = False
            if node_id is None:
                self._drag_mode = "right_pan"
                self._drag_node_id = None
                self._drag_target_ids = ()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self._drag_mode = "subtree" if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else "node"
                self._drag_node_id = node_id
                self._drag_target_ids = self._subtree_node_ids(node_id) if self._drag_mode == "subtree" else (node_id,)
                self._selected_node_id = node_id
                self.node_selected.emit(node_id)
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                self.update()
            event.accept()
            return

        super().mousePressEvent(event)

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

        if self._drag_mode in {"node", "subtree"}:
            if self._press_global_pos is None or self._last_global_pos is None or not event.buttons() & Qt.MouseButton.RightButton:
                super().mouseMoveEvent(event)
                return
            current = event.globalPosition()
            delta = current - self._last_global_pos
            total = current - self._press_global_pos
            if self._dragging or abs(total.x()) + abs(total.y()) > 4:
                self._dragging = True
                self._last_global_pos = current
                self._move_nodes(self._drag_target_ids, delta)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton and self._drag_mode in {"right_pan", "node", "subtree"}:
            self.unsetCursor()
            self._press_global_pos = None
            self._last_global_pos = None
            self._dragging = False
            self._drag_mode = None
            self._drag_node_id = None
            self._drag_target_ids = ()
            if getattr(self, "_layout_dirty", False):
                self._save_offsets()
                self._layout_dirty = False
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _node_at(self, pos: QPointF) -> str | None:
        positions = self._positions()
        candidates: list[tuple[float, str]] = []
        for node in self._nodes:
            if node.node_id not in positions:
                continue
            x, y = positions[node.node_id]
            dot_rect = QRectF(x - 18 * self._zoom, y - 18 * self._zoom, 36 * self._zoom, 36 * self._zoom)
            label_width = self._label_width(node.title)
            label_rect = QRectF(x + 20 * self._zoom, y - 17 * self._zoom, max(42.0, label_width + 22.0) * self._zoom, 34 * self._zoom)
            if dot_rect.contains(pos) or label_rect.contains(pos):
                distance = (pos.x() - x) ** 2 + (pos.y() - y) ** 2
                candidates.append((distance, node.node_id))
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[0])[1]

    def _lanes(self) -> dict[str, int]:
        children = self._children_by_id()
        by_id = {node.node_id: node for node in self._nodes}
        levels = self._display_levels()
        lanes = {node.node_id: 0 for node in self._nodes}
        occupancy: dict[int, list[tuple[int, int, float]]] = {}
        groups = self._branch_groups(children, by_id, levels)
        for group in sorted(groups, key=lambda item: (item["end"], item["start"]), reverse=True):
            lane = self._choose_free_lane(group, occupancy)
            for node_id in group["ids"]:
                lanes[str(node_id)] = lane
            occupancy.setdefault(lane, []).append((int(group["start"]), int(group["end"]), float(group["width"])))
        return lanes

    def _branch_groups(
        self,
        children: dict[str, list[str]],
        by_id: dict[str, object],
        levels: dict[str, int],
    ) -> list[dict[str, object]]:
        groups: list[dict[str, object]] = []
        for node in self._nodes:
            if not self._side(node):
                continue
            parent_id = self._parent(node)
            parent = by_id.get(parent_id) if parent_id is not None else None
            if parent is not None and self._side(parent):
                continue
            ids = self._collect_branch_ids(node.node_id, children, by_id)
            used_levels = [levels.get(node_id, self._level(by_id[node_id])) for node_id in ids if node_id in by_id]
            if not used_levels:
                continue
            groups.append(
                {
                    "ids": tuple(ids),
                    "start": min(used_levels),
                    "end": max(used_levels),
                    "width": max((self._label_width(by_id[node_id].title) for node_id in ids if node_id in by_id), default=120.0),
                }
            )
        return groups

    def _collect_branch_ids(self, root_id: str, children: dict[str, list[str]], by_id: dict[str, object]) -> tuple[str, ...]:
        result: list[str] = []

        def collect(node_id: str) -> None:
            if node_id in result or node_id not in by_id:
                return
            result.append(node_id)
            for child_id in children.get(node_id, []):
                collect(child_id)

        collect(root_id)
        return tuple(result)

    def _choose_free_lane(self, group: dict[str, object], occupancy: dict[int, list[tuple[int, int, float]]]) -> int:
        for lane in self._candidate_lanes():
            if self._lane_is_free(lane, group, occupancy):
                return lane
        return max((abs(lane) for lane in occupancy), default=0) + 1

    def _candidate_lanes(self) -> tuple[int, ...]:
        result: list[int] = []
        for step in range(1, 20):
            result.extend((step, -step))
        return tuple(result)

    def _lane_offsets(self, lanes: dict[str, int]) -> dict[int, float]:
        by_id = {node.node_id: node for node in self._nodes}
        lane_ids = sorted(set(lanes.values()))
        widths: dict[int, float] = {}
        parent_requirements: dict[int, float] = {}
        for node in self._nodes:
            lane = lanes.get(node.node_id, 0)
            if lane == 0:
                continue
            widths[lane] = max(widths.get(lane, 0.0), self._label_width(node.title))
            parent_id = self._parent(node)
            parent = by_id.get(parent_id) if parent_id is not None else None
            if parent is not None and not self._side(parent):
                parent_requirements[lane] = max(parent_requirements.get(lane, 0.0), self._label_width(parent.title) + 74.0)
        offsets: dict[int, float] = {0: 0.0}
        previous_offset = 0.0
        previous_width = 0.0
        for lane in [item for item in lane_ids if item > 0]:
            minimum = max(parent_requirements.get(lane, 0.0), 104.0)
            previous_offset = max(previous_offset + previous_width + 70.0, minimum)
            offsets[lane] = previous_offset
            previous_width = widths.get(lane, 112.0)
        previous_distance = 0.0
        for lane in sorted((item for item in lane_ids if item < 0), reverse=True):
            width = widths.get(lane, 112.0)
            previous_distance = max(previous_distance + width + 70.0, width + 70.0, 104.0)
            offsets[lane] = -previous_distance
        return offsets

    def _lane_is_free(self, lane: int, group: dict[str, object], occupancy: dict[int, list[tuple[int, int, float]]]) -> bool:
        start = int(group["start"])
        end = int(group["end"])
        width = float(group["width"])
        for other_start, other_end, other_width in occupancy.get(lane, []):
            if start <= other_end + 1 and other_start <= end + 1:
                return False
            if abs(start - other_end) <= 1 or abs(other_start - end) <= 1:
                if width + other_width > 180:
                    return False
        return True

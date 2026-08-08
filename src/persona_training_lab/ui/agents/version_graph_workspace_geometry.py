from __future__ import annotations

from math import ceil

from PySide6.QtCore import QPointF, Signal
from PySide6.QtGui import QMouseEvent

from persona_training_lab.ui.agents.version_graph_mouse_routing import (
    VersionGraphCanvas as MouseRoutingVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_workspace import (
    WorkspaceBounds,
    WorkspaceGeometry,
    build_workspace_geometry,
    grow_workspace_geometry,
)


class VersionGraphCanvas(MouseRoutingVersionGraphCanvas):
    """Maintain editable workspace geometry independently of input routing."""

    workspace_origin_shifted = Signal(QPointF)

    _HORIZONTAL_MARGIN = 1800.0
    _VERTICAL_MARGIN = 1100.0
    _MINIMUM_WORKSPACE_WIDTH = 3200.0
    _MINIMUM_WORKSPACE_HEIGHT = 2400.0
    _ROW_GAP = 52.0

    def __init__(self, nodes) -> None:
        self._workspace_geometry: WorkspaceGeometry | None = None
        super().__init__(nodes)
        # Persistent offsets are loaded inside the parent constructor, after the
        # first QWidget size pass, so rebuild once more with the real saved state.
        self._rebuild_workspace_geometry(emit_shift=False)

    def set_nodes(self, nodes) -> None:
        self._workspace_geometry = None
        super().set_nodes(nodes)

    def toggle_flipped(self) -> None:
        super().toggle_flipped()
        self._rebuild_workspace_geometry()

    def restore_layout_snapshot(self, snapshot) -> None:
        super().restore_layout_snapshot(snapshot)
        self._rebuild_workspace_geometry()

    def reset_layout(self) -> None:
        super().reset_layout()
        self._rebuild_workspace_geometry()

    def reset_node_layout(self, node_id: str) -> None:
        super().reset_node_layout(node_id)
        self._rebuild_workspace_geometry()

    def reset_subtree_layout(self, node_id: str) -> None:
        super().reset_subtree_layout(node_id)
        self._rebuild_workspace_geometry()

    def forget_layout_nodes(self, node_ids) -> None:
        super().forget_layout_nodes(node_ids)
        self._rebuild_workspace_geometry()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        self._rebuild_workspace_geometry()

    def _move_nodes(self, node_ids: tuple[str, ...], delta: QPointF) -> None:
        before = tuple(
            (node_id, self._node_offsets.get(node_id, QPointF()))
            for node_id in node_ids
        )
        super()._move_nodes(node_ids, delta)
        after = tuple(
            (node_id, self._node_offsets.get(node_id, QPointF()))
            for node_id in node_ids
        )
        if before != after:
            self._grow_workspace_to_current_content()

    def _refresh_size(self) -> None:
        self._ensure_workspace_geometry()
        self._apply_workspace_size()

    def _canvas_width(self) -> int:
        geometry = self._ensure_workspace_geometry()
        return max(1, int(ceil(geometry.width * self._zoom)))

    def _canvas_height(self) -> int:
        geometry = self._ensure_workspace_geometry()
        return max(1, int(ceil(geometry.height * self._zoom)))

    def _positions(self) -> dict[str, tuple[float, float]]:
        geometry = self._ensure_workspace_geometry()
        return {
            node_id: (
                (x + geometry.origin_x) * self._zoom,
                (y + geometry.origin_y) * self._zoom,
            )
            for node_id, (x, y) in self._raw_positions().items()
        }

    def _raw_positions(self) -> dict[str, tuple[float, float]]:
        lanes = self._lanes()
        lane_offsets = self._lane_offsets(lanes)
        levels = self._display_levels()
        max_level = max(levels.values(), default=0)
        result: dict[str, tuple[float, float]] = {}
        for node in self._nodes:
            level = levels.get(node.node_id, self._level(node))
            visual_level = max_level - level if self._flipped else level
            offset = self._node_offsets.get(node.node_id, QPointF())
            offset_y = -offset.y() if self._flipped else offset.y()
            result[node.node_id] = (
                lane_offsets.get(lanes.get(node.node_id, 0), 0.0) + offset.x(),
                visual_level * self._ROW_GAP + offset_y,
            )
        return result

    def _content_bounds(self) -> WorkspaceBounds:
        positions = self._raw_positions()
        if not positions:
            return WorkspaceBounds(-60.0, -60.0, 60.0, 60.0)

        by_id = {node.node_id: node for node in self._nodes}
        left = float("inf")
        top = float("inf")
        right = float("-inf")
        bottom = float("-inf")
        for node_id, (x, y) in positions.items():
            node = by_id.get(node_id)
            label_width = (
                self._label_width(node.title) if node is not None else 120.0
            )
            left = min(left, x - 34.0)
            top = min(top, y - 34.0)
            right = max(
                right,
                x + 28.0 + max(64.0, label_width + 28.0),
            )
            bottom = max(bottom, y + 34.0)
        return WorkspaceBounds(left, top, right, bottom)

    def _ensure_workspace_geometry(self) -> WorkspaceGeometry:
        if self._workspace_geometry is None:
            self._workspace_geometry = build_workspace_geometry(
                self._content_bounds(),
                horizontal_margin=self._HORIZONTAL_MARGIN,
                vertical_margin=self._VERTICAL_MARGIN,
                minimum_width=self._MINIMUM_WORKSPACE_WIDTH,
                minimum_height=self._MINIMUM_WORKSPACE_HEIGHT,
            )
        return self._workspace_geometry

    def _rebuild_workspace_geometry(self, *, emit_shift: bool = True) -> None:
        old = self._workspace_geometry
        new = build_workspace_geometry(
            self._content_bounds(),
            horizontal_margin=self._HORIZONTAL_MARGIN,
            vertical_margin=self._VERTICAL_MARGIN,
            minimum_width=self._MINIMUM_WORKSPACE_WIDTH,
            minimum_height=self._MINIMUM_WORKSPACE_HEIGHT,
        )
        self._workspace_geometry = new
        self._apply_workspace_size()
        if old is not None and emit_shift:
            delta = QPointF(
                (new.origin_x - old.origin_x) * self._zoom,
                (new.origin_y - old.origin_y) * self._zoom,
            )
            if abs(delta.x()) > 0.5 or abs(delta.y()) > 0.5:
                self.workspace_origin_shifted.emit(delta)

    def _grow_workspace_to_current_content(self) -> None:
        geometry = self._ensure_workspace_geometry()
        grown = grow_workspace_geometry(
            geometry,
            self._content_bounds(),
            horizontal_margin=self._HORIZONTAL_MARGIN,
            vertical_margin=self._VERTICAL_MARGIN,
        )
        if grown != geometry:
            self._workspace_geometry = grown
            self._apply_workspace_size()

    def _apply_workspace_size(self) -> None:
        width = self._canvas_width()
        height = self._canvas_height()
        if self.minimumWidth() != width or self.minimumHeight() != height:
            self.setMinimumSize(width, height)
        if self.width() != width or self.height() != height:
            self.resize(width, height)
        self.updateGeometry()
        self.update()

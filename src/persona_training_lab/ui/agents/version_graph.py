from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen, QRadialGradient, QWheelEvent
from PySide6.QtWidgets import QWidget

from persona_training_lab.ui.viewmodels.agents import VersionNodeView


class VersionGraphCanvas(QWidget):
    node_selected = Signal(str)
    zoom_changed = Signal(float)
    pan_requested = Signal(QPointF)

    def __init__(self, nodes: tuple[VersionNodeView, ...]) -> None:
        super().__init__()
        self._nodes = nodes
        self._selected_node_id = "snapshot"
        self._hit_rects: dict[str, QRectF] = {}
        self._zoom = 1.0
        self._flipped = False
        self._press_pos: QPointF | None = None
        self._last_drag_pos: QPointF | None = None
        self._dragging = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._refresh_size()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._canvas_width(), self._canvas_height())

    def set_selected(self, node_id: str) -> None:
        self._selected_node_id = node_id
        self.update()

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.65, min(1.8, zoom))
        self._refresh_size()
        self.updateGeometry()
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def reset_zoom(self) -> None:
        self.set_zoom(1.0)
        self.zoom_changed.emit(self._zoom)

    def toggle_flipped(self) -> None:
        self._flipped = not self._flipped
        self.update()

    def node_center(self, node_id: str) -> QPointF:
        return QPointF(*self._positions_by_id().get(node_id, (self.width() / 2, self.height() / 2)))

    def current_node_id(self) -> str:
        for node in self._nodes:
            if getattr(node, "is_current", False) or node.branch_note == "current":
                return node.node_id
        return "snapshot"

    def paintEvent(self, _event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self._hit_rects.clear()
        positions = self._positions_by_id()
        nodes_by_id = {node.node_id: node for node in self._nodes}

        for node in self._nodes:
            parent_id = self._parent_id(node)
            if parent_id is None or parent_id not in positions or node.node_id not in positions:
                continue
            px, py = positions[parent_id]
            x, y = positions[node.node_id]
            parent_tone = nodes_by_id[parent_id].tone if parent_id in nodes_by_id else node.tone
            tone = node.tone if node.branch_note not in {"main", "current"} else parent_tone
            self._draw_connector(painter, px, py, x, y, tone)

        for node in self._ordered_nodes_for_paint():
            x, y = positions[node.node_id]
            self._draw_node(painter, node, x, y, self._label_x(x))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position()
            self._last_drag_pos = event.position()
            self._dragging = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._press_pos is None or self._last_drag_pos is None or not event.buttons() & Qt.MouseButton.LeftButton:
            super().mouseMoveEvent(event)
            return
        delta = event.position() - self._last_drag_pos
        total = event.position() - self._press_pos
        if self._dragging or abs(total.x()) + abs(total.y()) > 4:
            self._dragging = True
            self._last_drag_pos = event.position()
            self.pan_requested.emit(delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        self.unsetCursor()
        pos = event.position()
        was_dragging = self._dragging
        self._press_pos = None
        self._last_drag_pos = None
        self._dragging = False
        if was_dragging:
            event.accept()
            return
        for node_id, rect in self._hit_rects.items():
            if rect.contains(pos):
                self._selected_node_id = node_id
                self.update()
                self.node_selected.emit(node_id)
                event.accept()
                return
        event.accept()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        self.set_zoom(self._zoom + (0.08 if delta > 0 else -0.08))
        self.zoom_changed.emit(self._zoom)
        event.accept()

    def _refresh_size(self) -> None:
        self.setMinimumSize(self._canvas_width(), self._canvas_height())
        self.resize(self._canvas_width(), self._canvas_height())

    def _canvas_width(self) -> int:
        return int((620 + 1800) * self._zoom)

    def _canvas_height(self) -> int:
        graph_height = 80 + (self._max_level() + 1) * 52
        return max(620, int((graph_height + 1400) * self._zoom))

    def _positions_by_id(self) -> dict[str, tuple[float, float]]:
        row_gap = 52 * self._zoom
        top = 700 * self._zoom + 38 * self._zoom
        axis_x = 900 * self._zoom + 150 * self._zoom
        branch_step = 64 * self._zoom
        max_level = self._max_level()
        lanes = self._lanes_by_id()
        levels = self._levels_by_id()
        positions: dict[str, tuple[float, float]] = {}
        for node in self._nodes:
            level = levels.get(node.node_id, 0)
            visual_level = max_level - level if self._flipped else level
            positions[node.node_id] = (axis_x + lanes.get(node.node_id, 0) * branch_step, top + visual_level * row_gap)
        return positions

    def _parent_id(self, node: VersionNodeView) -> str | None:
        explicit = getattr(node, "parent_id", None)
        if explicit is not None:
            return explicit
        fallback = {
            "base": None,
            "dataset": "base",
            "training": "dataset",
            "snapshot": "training",
            "portrait": "snapshot",
            "delta": "snapshot" if node.tone == "pending" else "portrait",
            "accepted_delta": "portrait",
            "unclear_branch": "snapshot",
        }
        return fallback.get(node.node_id)

    def _levels_by_id(self) -> dict[str, int]:
        nodes = {node.node_id: node for node in self._nodes}
        cache: dict[str, int] = {}

        def level(node_id: str) -> int:
            if node_id in cache:
                return cache[node_id]
            parent_id = self._parent_id(nodes[node_id])
            cache[node_id] = 0 if parent_id is None or parent_id not in nodes else level(parent_id) + 1
            return cache[node_id]

        for node in self._nodes:
            level(node.node_id)
        return cache

    def _lanes_by_id(self) -> dict[str, int]:
        children: dict[str | None, list[VersionNodeView]] = {}
        for node in self._nodes:
            children.setdefault(self._parent_id(node), []).append(node)
        lanes: dict[str, int] = {}

        def assign(node: VersionNodeView, lane: int) -> None:
            lanes[node.node_id] = lane
            node_children = children.get(node.node_id, [])
            main_children = [child for child in node_children if child.branch_note in {"main", "current"}]
            side_children = [child for child in node_children if child.branch_note not in {"main", "current"}]
            for child in main_children:
                assign(child, lane)
            for offset, child in enumerate(side_children, start=1):
                assign(child, lane + offset)

        for root in children.get(None, []):
            assign(root, 0)
        return lanes

    def _max_level(self) -> int:
        return max(self._levels_by_id().values(), default=0)

    def _ordered_nodes_for_paint(self) -> tuple[VersionNodeView, ...]:
        lanes = self._lanes_by_id()
        levels = self._levels_by_id()
        return tuple(sorted(self._nodes, key=lambda node: (levels.get(node.node_id, 0), lanes.get(node.node_id, 0))))

    def _label_x(self, node_x: float) -> float:
        return node_x + 28 * self._zoom

    def _draw_connector(self, painter: QPainter, px: float, py: float, x: float, y: float, tone: str) -> None:
        color = self._tone_color(tone)
        color.setAlpha(150)
        pen = QPen(color, max(1.2, 1.8 * self._zoom))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        dot_gap = 9 * self._zoom
        if px == x:
            painter.drawLine(QPointF(px, py + dot_gap if y > py else py - dot_gap), QPointF(x, y - dot_gap if y > py else y + dot_gap))
            return
        mid_y = (py + y) / 2
        painter.drawLine(QPointF(px, py + dot_gap if y > py else py - dot_gap), QPointF(px, mid_y))
        painter.drawLine(QPointF(px, mid_y), QPointF(x, mid_y))
        painter.drawLine(QPointF(x, mid_y), QPointF(x, y - dot_gap if y > py else y + dot_gap))

    def _draw_node(self, painter: QPainter, node: VersionNodeView, x: float, y: float, label_x: float) -> None:
        selected = node.node_id == self._selected_node_id
        color = self._tone_color(node.tone)
        radius = 5.3 * self._zoom if not selected else 6.3 * self._zoom
        self._draw_soft_glow(painter, x, y, color, selected)
        if selected:
            painter.setPen(QPen(QColor(34, 211, 238, 210), max(1.0, 1.45 * self._zoom)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(x, y), 9.4 * self._zoom, 9.4 * self._zoom)
        painter.setPen(QPen(QColor(15, 23, 42, 240), max(0.7, 1.0 * self._zoom)))
        painter.setBrush(color)
        painter.drawEllipse(QPointF(x, y), radius, radius)
        self._draw_label(painter, node, label_x, y, selected)
        self._hit_rects[node.node_id] = QRectF(x - 20 * self._zoom, y - 20 * self._zoom, max(420 * self._zoom, self.width() - x - 20), 40 * self._zoom)

    def _draw_label(self, painter: QPainter, node: VersionNodeView, label_x: float, y: float, selected: bool) -> None:
        label = self._display_label(node.title)
        font = QFont(painter.font())
        font.setPointSizeF(max(8.5, 10.0 * self._zoom))
        font.setBold(selected)
        painter.setFont(font)
        painter.setPen(QColor(226, 232, 240) if selected else QColor(203, 213, 225))
        label_rect = QRectF(label_x, y - 13 * self._zoom, max(230, self.width() - label_x - 24), 26 * self._zoom)
        painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignLeft, label)
        badge = self._status_badge(node)
        if not badge:
            return
        badge_x = label_x + min(260 * self._zoom, max(100 * self._zoom, len(label) * 7.2 * self._zoom + 12))
        badge_rect = QRectF(badge_x, y - 10 * self._zoom, 86 * self._zoom, 20 * self._zoom)
        painter.setPen(QPen(QColor(148, 163, 184, 88), max(0.8, self._zoom)))
        painter.setBrush(QColor(15, 23, 42, 116))
        painter.drawRoundedRect(badge_rect, 9 * self._zoom, 9 * self._zoom)
        badge_font = QFont(painter.font())
        badge_font.setPointSizeF(max(7.0, 8.0 * self._zoom))
        badge_font.setBold(True)
        painter.setFont(badge_font)
        painter.setPen(QColor(148, 163, 184))
        painter.drawText(badge_rect, Qt.AlignCenter, badge)

    def _draw_soft_glow(self, painter: QPainter, x: float, y: float, color: QColor, selected: bool) -> None:
        glow_radius = (14 if selected else 10) * self._zoom
        center = QColor(color)
        center.setAlpha(58 if selected else 34)
        mid = QColor(color)
        mid.setAlpha(18 if selected else 10)
        edge = QColor(color)
        edge.setAlpha(0)
        gradient = QRadialGradient(QPointF(x, y), glow_radius)
        gradient.setColorAt(0.0, center)
        gradient.setColorAt(0.45, mid)
        gradient.setColorAt(1.0, edge)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(QPointF(x, y), glow_radius, glow_radius)

    def _tone_color(self, tone: str) -> QColor:
        if tone == "bad":
            return QColor("#ef4444")
        if tone == "pending":
            return QColor("#f59e0b")
        if tone == "neutral":
            return QColor("#94a3b8")
        return QColor("#22c55e")

    def _display_label(self, title: str) -> str:
        for prefix in ("Base · ", "Dataset · ", "Train · ", "Version · ", "Portrait · ", "Delta · "):
            if title.startswith(prefix):
                return title.removeprefix(prefix)
        return title

    def _status_badge(self, node: VersionNodeView) -> str:
        if getattr(node, "is_current", False) or node.branch_note == "current":
            return "current"
        if node.branch_note not in {"main", "current"}:
            return "branch"
        if node.tone == "bad":
            return "failed"
        if node.tone == "pending":
            return "pending"
        return ""

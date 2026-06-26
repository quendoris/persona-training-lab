from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen, QRadialGradient, QWheelEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.viewmodels.agents import AgentDetailView, AgentsViewModel, VersionNodeView


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

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
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
        for node, x, y in self._positions():
            if node.node_id == node_id:
                return QPointF(x, y)
        return QPointF(self.width() / 2, self.height() / 2)

    def current_node_id(self) -> str:
        for node in self._nodes:
            if node.branch_note == "current":
                return node.node_id
        return "snapshot"

    def paintEvent(self, _event: QPaintEvent) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self._hit_rects.clear()

        positions = self._positions()
        for index, (node, x, y) in enumerate(positions):
            if index > 0:
                _prev_node, px, py = positions[index - 1]
                self._draw_connector(painter, px, py, x, y, node.tone)
        for node, x, y in positions:
            self._draw_node(painter, node, x, y, self._label_x(x))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position()
            self._last_drag_pos = event.position()
            self._dragging = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        if self._press_pos is None or self._last_drag_pos is None:
            super().mouseMoveEvent(event)
            return
        if not event.buttons() & Qt.MouseButton.LeftButton:
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

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
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

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt override
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
        graph_height = 80 + max(1, len(self._nodes)) * 52
        return max(620, int((graph_height + 1400) * self._zoom))

    def _horizontal_padding(self) -> float:
        return 900 * self._zoom

    def _vertical_padding(self) -> float:
        return 700 * self._zoom

    def _positions(self) -> list[tuple[VersionNodeView, float, float]]:
        row_gap = 52 * self._zoom
        top = self._vertical_padding() + 38 * self._zoom
        axis_x = self._horizontal_padding() + 150 * self._zoom
        branch_step = 34 * self._zoom
        total = len(self._nodes)
        positions: list[tuple[VersionNodeView, float, float]] = []
        for index, node in enumerate(self._nodes):
            order_index = total - 1 - index if self._flipped else index
            x = axis_x + self._lane_for(node) * branch_step
            y = top + order_index * row_gap
            positions.append((node, float(x), float(y)))
        return positions

    def _label_x(self, node_x: float) -> float:
        return node_x + 28 * self._zoom

    def _lane_for(self, node: VersionNodeView) -> int:
        if node.tone == "bad":
            return 1
        if node.branch_note not in {"main", "current"}:
            return 1
        return 0

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

        label = self._display_label(node.title)
        font = QFont(painter.font())
        font.setPointSizeF(max(8.5, 10.0 * self._zoom))
        font.setBold(selected)
        painter.setFont(font)
        painter.setPen(QColor(226, 232, 240) if selected else QColor(203, 213, 225))
        label_rect = QRectF(label_x, y - 13 * self._zoom, max(230, self.width() - label_x - 24), 26 * self._zoom)
        painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignLeft, label)

        badge = self._status_badge(node)
        if badge:
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

        self._hit_rects[node.node_id] = QRectF(x - 20 * self._zoom, y - 20 * self._zoom, max(420 * self._zoom, self.width() - x - 20), 40 * self._zoom)

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
        if node.branch_note == "current":
            return "current"
        if node.tone == "bad":
            return "failed"
        if node.tone == "pending":
            return "pending"
        return ""


class AgentsScreen(QWidget):
    def __init__(self, view_model: AgentsViewModel) -> None:
        super().__init__()
        self._vm = view_model
        self._selected_node_id = "snapshot"

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        title, subtitle = self._vm.header_summary()

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(8)
        header_title = QLabel(title)
        header_title.setObjectName("ScreenTitle")
        header_layout.addWidget(header_title)
        header_layout.addWidget(make_muted_label(subtitle))
        root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left_column = QWidget()
        left_column.setProperty("transparentBg", True)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        roles_card = PanelCard("Рабочие роли", "Роли не действуют автономно: они подсказывают следующий шаг.")
        for role in self._vm.roles():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(6)
            top = QHBoxLayout()
            title_label = QLabel(role.title)
            title_label.setObjectName("CardTitle")
            top.addWidget(title_label, 1)
            top.addWidget(make_status_label(role.status, warning=role.status in {"позже", "проверка"}))
            row_layout.addLayout(top)
            row_layout.addWidget(make_muted_label(role.mission))
            next_label = QLabel(f"→ {role.next_action}")
            next_label.setWordWrap(True)
            row_layout.addWidget(next_label)
            roles_card.add_widget(row)
        left_layout.addWidget(roles_card)
        left_layout.addStretch(1)
        body.addWidget(left_column, 2)

        timeline_card = PanelCard("Дерево версий", "SmartGit‑стиль: граф точек по центру, детали выбранного узла справа.")
        controls = QHBoxLayout()
        controls.setSpacing(8)
        self._center_button = self._control_button("К актуальной")
        self._flip_button = self._control_button("Отразить")
        self._reset_zoom_button = self._control_button("Масштаб 100%")
        controls.addStretch(1)
        controls.addWidget(self._center_button)
        controls.addWidget(self._flip_button)
        controls.addWidget(self._reset_zoom_button)
        controls.addStretch(1)
        timeline_card._layout.addLayout(controls)

        self._graph = VersionGraphCanvas(self._vm.version_nodes())
        self._graph.node_selected.connect(self._select_node)
        self._graph.zoom_changed.connect(self._on_graph_zoom_changed)
        self._graph.pan_requested.connect(self._pan_graph)
        self._scroll = QScrollArea()
        self._scroll.setObjectName("VersionTimelineScroll")
        self._scroll.setWidgetResizable(False)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setWidget(self._graph)
        timeline_card.add_widget(self._scroll)
        body.addWidget(timeline_card, 3)

        self._center_button.clicked.connect(self._center_current_node)
        self._flip_button.clicked.connect(self._flip_graph)
        self._reset_zoom_button.clicked.connect(self._reset_zoom)

        right_column = QWidget()
        right_column.setProperty("transparentBg", True)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        detail_card = PanelCard("Карточка узла", "Коммиты, параметры, KPI и действия — здесь, не в графе.")
        self._detail_title = QLabel("—")
        self._detail_title.setObjectName("CardTitle")
        self._detail_body = QLabel("Выберите узел дерева.")
        self._detail_body.setWordWrap(True)
        detail_card.add_widget(self._detail_title)
        detail_card.add_widget(self._detail_body)

        self._checks_title = QLabel("Проверить")
        self._checks_title.setObjectName("CardTitle")
        detail_card.add_widget(self._checks_title)
        self._checks_layout = QGridLayout()
        self._checks_layout.setSpacing(8)
        detail_card._layout.addLayout(self._checks_layout)

        self._actions_title = QLabel("Доступные действия")
        self._actions_title.setObjectName("CardTitle")
        detail_card.add_widget(self._actions_title)
        self._actions_layout = QGridLayout()
        self._actions_layout.setSpacing(8)
        detail_card._layout.addLayout(self._actions_layout)
        right_layout.addWidget(detail_card)
        right_layout.addStretch(1)
        body.addWidget(right_column, 2)

        self._select_node(self._graph.current_node_id())
        QTimer.singleShot(0, self._center_current_node)

    def _control_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("SecondaryButton")
        button.setMinimumHeight(32)
        return button

    def _select_node(self, node_id: str) -> None:
        self._selected_node_id = node_id
        self._graph.set_selected(node_id)
        self._render_detail(self._vm.node_detail(node_id))

    def _center_current_node(self) -> None:
        self._select_node(self._graph.current_node_id())
        self._center_on_node(self._selected_node_id)

    def _center_on_node(self, node_id: str) -> None:
        point = self._graph.node_center(node_id)
        viewport = self._scroll.viewport().size()
        hbar = self._scroll.horizontalScrollBar()
        vbar = self._scroll.verticalScrollBar()
        hbar.setValue(max(0, int(point.x() - viewport.width() / 2)))
        vbar.setValue(max(0, int(point.y() - viewport.height() / 2)))

    def _flip_graph(self) -> None:
        self._graph.toggle_flipped()
        QTimer.singleShot(0, lambda: self._center_on_node(self._selected_node_id))

    def _reset_zoom(self) -> None:
        self._graph.reset_zoom()
        QTimer.singleShot(0, lambda: self._center_on_node(self._selected_node_id))

    def _on_graph_zoom_changed(self, _zoom: float) -> None:
        pass

    def _pan_graph(self, delta: QPointF) -> None:
        hbar = self._scroll.horizontalScrollBar()
        vbar = self._scroll.verticalScrollBar()
        hbar.setValue(hbar.value() - int(delta.x()))
        vbar.setValue(vbar.value() - int(delta.y()))

    def _render_detail(self, detail: AgentDetailView) -> None:
        self._detail_title.setText(detail.title)
        self._detail_body.setText(detail.body)
        self._fill_list_layout(self._checks_layout, detail.checks, "✓")
        self._fill_list_layout(self._actions_layout, detail.actions, "→")

    def _fill_list_layout(self, layout: QGridLayout, values: tuple[str, ...], prefix: str) -> None:
        self._clear_layout(layout)
        if not values:
            values = ("Нет доступных действий",)
            prefix = "•"
        for index, value in enumerate(values):
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(8)
            row_layout.addWidget(QLabel(prefix))
            label = make_muted_label(value)
            row_layout.addWidget(label, 1)
            layout.addWidget(row, index, 0)

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child = item.layout()
            widget = item.widget()
            if child is not None:
                self._clear_layout(child)
            if widget is not None:
                widget.deleteLater()

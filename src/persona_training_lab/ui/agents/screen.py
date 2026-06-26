from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QScrollArea, QVBoxLayout, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.viewmodels.agents import AgentDetailView, AgentsViewModel, VersionNodeView


class VersionGraphCanvas(QWidget):
    node_selected = Signal(str)

    def __init__(self, nodes: tuple[VersionNodeView, ...]) -> None:
        super().__init__()
        self._nodes = nodes
        self._selected_node_id = "snapshot"
        self._hit_rects: dict[str, QRectF] = {}
        self.setMouseTracking(True)
        self.setMinimumHeight(max(360, 52 + len(nodes) * 64))
        self.setMinimumWidth(520)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(620, max(380, 52 + len(self._nodes) * 64))

    def set_selected(self, node_id: str) -> None:
        self._selected_node_id = node_id
        self.update()

    def paintEvent(self, _event: QPaintEvent) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self._hit_rects.clear()

        row_gap = 62
        top = 30
        axis_x = max(68, min(132, self.width() // 2 - 190))
        label_x = axis_x + 34
        branch_step = 30
        positions: list[tuple[VersionNodeView, float, float]] = []
        for index, node in enumerate(self._nodes):
            x = axis_x + self._lane_for(node) * branch_step
            y = top + index * row_gap
            positions.append((node, float(x), float(y)))

        for index, (node, x, y) in enumerate(positions):
            if index > 0:
                _prev_node, px, py = positions[index - 1]
                self._draw_connector(painter, px, py, x, y)
            self._draw_node(painter, node, x, y, label_x + self._lane_for(node) * branch_step)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override
        pos = event.position()
        for node_id, rect in self._hit_rects.items():
            if rect.contains(pos):
                self._selected_node_id = node_id
                self.update()
                self.node_selected.emit(node_id)
                return
        super().mousePressEvent(event)

    def _lane_for(self, node: VersionNodeView) -> int:
        if node.tone == "bad":
            return 1
        if node.branch_note not in {"main", "current"}:
            return 1
        return 0

    def _draw_connector(self, painter: QPainter, px: float, py: float, x: float, y: float) -> None:
        pen = QPen(QColor(100, 116, 139, 180), 2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        if px == x:
            painter.drawLine(QPointF(px, py + 8), QPointF(x, y - 8))
            return
        mid_y = (py + y) / 2
        painter.drawLine(QPointF(px, py + 8), QPointF(px, mid_y))
        painter.drawLine(QPointF(px, mid_y), QPointF(x, mid_y))
        painter.drawLine(QPointF(x, mid_y), QPointF(x, y - 8))

    def _draw_node(self, painter: QPainter, node: VersionNodeView, x: float, y: float, label_x: float) -> None:
        selected = node.node_id == self._selected_node_id
        color = self._tone_color(node.tone)
        radius = 6.2 if not selected else 7.8

        if selected:
            painter.setPen(QPen(QColor(34, 211, 238, 210), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(x, y), 12, 12)

        painter.setPen(QPen(QColor(15, 23, 42, 230), 1.3))
        painter.setBrush(color)
        painter.drawEllipse(QPointF(x, y), radius, radius)

        label = self._display_label(node.title)
        font = QFont(painter.font())
        font.setPointSize(10)
        font.setBold(selected)
        painter.setFont(font)
        painter.setPen(QColor(226, 232, 240) if selected else QColor(203, 213, 225))
        label_rect = QRectF(label_x, y - 12, max(260, self.width() - label_x - 28), 24)
        painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignLeft, label)

        badge = self._status_badge(node)
        if badge:
            badge_x = label_x + min(250, max(110, len(label) * 7 + 12))
            badge_rect = QRectF(badge_x, y - 10, 92, 20)
            painter.setPen(QPen(QColor(148, 163, 184, 90), 1))
            painter.setBrush(QColor(15, 23, 42, 110))
            painter.drawRoundedRect(badge_rect, 9, 9)
            badge_font = QFont(painter.font())
            badge_font.setPointSize(8)
            badge_font.setBold(True)
            painter.setFont(badge_font)
            painter.setPen(QColor(148, 163, 184))
            painter.drawText(badge_rect, Qt.AlignCenter, badge)

        self._hit_rects[node.node_id] = QRectF(x - 18, y - 20, max(420, self.width() - x - 24), 40)

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
        self._graph = VersionGraphCanvas(self._vm.version_nodes())
        self._graph.node_selected.connect(self._select_node)
        timeline_scroll = QScrollArea()
        timeline_scroll.setObjectName("VersionTimelineScroll")
        timeline_scroll.setWidgetResizable(True)
        timeline_scroll.setFrameShape(QFrame.NoFrame)
        timeline_scroll.setWidget(self._graph)
        timeline_card.add_widget(timeline_scroll)
        body.addWidget(timeline_card, 3)

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

        self._select_node("snapshot")

    def _select_node(self, node_id: str) -> None:
        self._selected_node_id = node_id
        self._graph.set_selected(node_id)
        self._render_detail(self._vm.node_detail(node_id))

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

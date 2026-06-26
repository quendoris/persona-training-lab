from __future__ import annotations

from PySide6.QtCore import Qt
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


class AgentsScreen(QWidget):
    def __init__(self, view_model: AgentsViewModel) -> None:
        super().__init__()
        self._vm = view_model
        self._node_buttons: dict[str, QPushButton] = {}
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

        timeline_card = PanelCard("Дерево версий", "Версии идут вниз как история модели. Неудачные ветки будут уходить в сторону.")
        self._timeline_host = QWidget()
        self._timeline_host.setProperty("transparentBg", True)
        self._timeline_layout = QVBoxLayout(self._timeline_host)
        self._timeline_layout.setContentsMargins(4, 4, 4, 4)
        self._timeline_layout.setSpacing(10)
        self._populate_timeline(self._vm.version_nodes())

        timeline_scroll = QScrollArea()
        timeline_scroll.setObjectName("VersionTimelineScroll")
        timeline_scroll.setWidgetResizable(True)
        timeline_scroll.setFrameShape(QFrame.NoFrame)
        timeline_scroll.setWidget(self._timeline_host)
        timeline_card.add_widget(timeline_scroll)
        body.addWidget(timeline_card, 3)

        right_column = QWidget()
        right_column.setProperty("transparentBg", True)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        detail_card = PanelCard("Карточка узла", "Параметры выбранной точки lineage и действия без автомагии.")
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

    def _populate_timeline(self, nodes: tuple[VersionNodeView, ...]) -> None:
        self._node_buttons.clear()
        for index, node in enumerate(nodes):
            if index > 0:
                connector = QLabel("│")
                connector.setStyleSheet("color: rgba(148, 163, 184, 0.55); font-size: 22px; font-weight: 800;")
                connector.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                connector.setContentsMargins(30 + node.depth * 22, 0, 0, 0)
                self._timeline_layout.addWidget(connector)
            row = self._make_timeline_row(node)
            self._timeline_layout.addWidget(row)
        self._timeline_layout.addStretch(1)

    def _make_timeline_row(self, node: VersionNodeView) -> QFrame:
        row = QFrame()
        row.setObjectName("VersionTimelineRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10 + node.depth * 22, 8, 10, 8)
        row_layout.setSpacing(12)

        dot = QLabel("●")
        dot.setStyleSheet(self._dot_style(node.tone))
        dot.setFixedSize(30, 30)
        dot.setAlignment(Qt.AlignCenter)
        row_layout.addWidget(dot, 0, Qt.AlignTop)

        button = QPushButton()
        button.setObjectName("VersionNodeButton")
        button.setStyleSheet(self._node_button_style())
        button.setCheckable(True)
        button.clicked.connect(lambda _checked=False, node_id=node.node_id: self._select_node(node_id))
        button_layout = QVBoxLayout(button)
        button_layout.setContentsMargins(12, 10, 12, 10)
        button_layout.setSpacing(6)
        top = QHBoxLayout()
        title = QLabel(node.title)
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        top.addWidget(title, 1)
        top.addWidget(make_status_label(node.branch_note if node.branch_note != "main" else node.status, warning=node.tone in {"pending", "bad"}))
        button_layout.addLayout(top)
        button_layout.addWidget(make_muted_label(node.subtitle))
        row_layout.addWidget(button, 1)
        self._node_buttons[node.node_id] = button
        return row

    def _dot_style(self, tone: str) -> str:
        if tone == "bad":
            return "color: #ef4444; font-size: 28px; font-weight: 900; background: transparent;"
        if tone == "pending":
            return "color: #f59e0b; font-size: 28px; font-weight: 900; background: transparent;"
        return "color: #22c55e; font-size: 28px; font-weight: 900; background: transparent;"

    def _node_button_style(self) -> str:
        return """
        QPushButton#VersionNodeButton {
            background-color: rgba(15, 23, 42, 0.35);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 18px;
            padding: 0px;
            text-align: left;
        }
        QPushButton#VersionNodeButton:hover {
            background-color: rgba(30, 41, 59, 0.72);
            border: 1px solid rgba(34, 211, 238, 0.55);
        }
        QPushButton#VersionNodeButton:checked {
            background-color: rgba(34, 211, 238, 0.14);
            border: 1px solid rgba(34, 211, 238, 0.85);
        }
        """

    def _select_node(self, node_id: str) -> None:
        self._selected_node_id = node_id
        for current_id, button in self._node_buttons.items():
            button.setChecked(current_id == node_id)
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

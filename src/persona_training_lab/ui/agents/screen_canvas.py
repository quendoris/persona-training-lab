from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

from persona_training_lab.ui.agents.version_graph_tree import VersionGraphCanvas
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.viewmodels.agents import AgentDetailView, AgentsViewModel


class AgentsScreen(QWidget):
    def __init__(self, view_model: AgentsViewModel) -> None:
        super().__init__()
        self._vm = view_model
        self._selected_node_id = "snapshot"
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)
        title, subtitle = self._vm.header_summary()
        root.addWidget(self._header(title, subtitle))
        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)
        body.addWidget(self._roles(), 2)
        body.addWidget(self._graph_panel(), 3)
        body.addWidget(self._details(), 2)
        self._select_node(self._graph.current_node_id())
        QTimer.singleShot(0, self._center_current_node)

    def _header(self, title: str, subtitle: str) -> QFrame:
        header = QFrame()
        header.setObjectName("ShellHeader")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(22, 18, 22, 18)
        label = QLabel(title)
        label.setObjectName("ScreenTitle")
        layout.addWidget(label)
        layout.addWidget(make_muted_label(subtitle))
        return header

    def _roles(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        card = PanelCard("Рабочие роли", "Короткие подсказки по текущему состоянию.")
        for role in self._vm.roles():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            top = QHBoxLayout()
            name = QLabel(role.title)
            name.setObjectName("CardTitle")
            top.addWidget(name, 1)
            top.addWidget(make_status_label(role.status, warning=role.status in {"позже", "проверка"}))
            row_layout.addLayout(top)
            row_layout.addWidget(make_muted_label(role.mission))
            hint = QLabel(f"→ {role.next_action}")
            hint.setWordWrap(True)
            row_layout.addWidget(hint)
            card.add_widget(row)
        layout.addWidget(card)
        layout.addStretch(1)
        return column

    def _graph_panel(self) -> QWidget:
        card = PanelCard("Дерево версий", "Граф lineage; подробности выбранной точки справа.")
        controls = QHBoxLayout()
        self._center_button = self._button("К актуальной")
        self._flip_button = self._button("Отразить")
        self._reset_button = self._button("Масштаб 100%")
        controls.addStretch(1)
        controls.addWidget(self._center_button)
        controls.addWidget(self._flip_button)
        controls.addWidget(self._reset_button)
        controls.addStretch(1)
        card._layout.addLayout(controls)
        self._graph = VersionGraphCanvas(self._vm.version_nodes())
        self._graph.node_selected.connect(self._select_node)
        self._graph.pan_requested.connect(self._pan_graph)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setWidget(self._graph)
        card.add_widget(self._scroll)
        self._center_button.clicked.connect(self._center_current_node)
        self._flip_button.clicked.connect(self._flip_graph)
        self._reset_button.clicked.connect(self._reset_zoom)
        return card

    def _details(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        card = PanelCard("Карточка узла", "Параметры, проверки и будущие действия.")
        self._detail_title = QLabel("—")
        self._detail_title.setObjectName("CardTitle")
        self._detail_body = QLabel("—")
        self._detail_body.setWordWrap(True)
        card.add_widget(self._detail_title)
        card.add_widget(self._detail_body)
        card.add_widget(QLabel("Проверить"))
        self._checks_layout = QGridLayout()
        card._layout.addLayout(self._checks_layout)
        card.add_widget(QLabel("Действия"))
        self._actions_layout = QGridLayout()
        card._layout.addLayout(self._actions_layout)
        layout.addWidget(card)
        layout.addStretch(1)
        return column

    def _button(self, text: str) -> QPushButton:
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
        self._scroll.horizontalScrollBar().setValue(max(0, int(point.x() - viewport.width() / 2)))
        self._scroll.verticalScrollBar().setValue(max(0, int(point.y() - viewport.height() / 2)))

    def _flip_graph(self) -> None:
        self._graph.toggle_flipped()
        QTimer.singleShot(0, lambda: self._center_on_node(self._selected_node_id))

    def _reset_zoom(self) -> None:
        self._graph.reset_zoom()
        QTimer.singleShot(0, lambda: self._center_on_node(self._selected_node_id))

    def _pan_graph(self, delta: QPointF) -> None:
        self._scroll.horizontalScrollBar().setValue(self._scroll.horizontalScrollBar().value() - int(delta.x()))
        self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().value() - int(delta.y()))

    def _render_detail(self, detail: AgentDetailView) -> None:
        self._detail_title.setText(detail.title)
        self._detail_body.setText(detail.body)
        self._fill(self._checks_layout, detail.checks, "✓")
        self._fill(self._actions_layout, detail.actions, "→")

    def _fill(self, layout: QGridLayout, values: tuple[str, ...], prefix: str) -> None:
        self._clear(layout)
        for index, value in enumerate(values or ("—",)):
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.addWidget(QLabel(prefix))
            row_layout.addWidget(make_muted_label(value), 1)
            layout.addWidget(row, index, 0)

    def _clear(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child = item.layout()
            widget = item.widget()
            if child is not None:
                self._clear(child)
            if widget is not None:
                widget.deleteLater()

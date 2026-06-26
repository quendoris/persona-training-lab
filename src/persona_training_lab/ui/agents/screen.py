from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QTreeWidget,
    QTreeWidgetItem,
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
        body.addWidget(roles_card, 2)

        lineage_card = PanelCard("Дерево версии", "Выберите узел, чтобы увидеть параметры и безопасные действия.")
        self._tree = QTreeWidget()
        self._tree.setObjectName("AgentsVersionTree")
        self._tree.setHeaderLabels(["Узел", "Статус"])
        self._tree.setColumnWidth(0, 260)
        self._populate_tree(self._vm.version_nodes())
        self._tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        lineage_card.add_widget(self._tree)
        body.addWidget(lineage_card, 3)

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
        body.addWidget(detail_card, 2)

        self._select_first_tree_item()
        root.addStretch(0)

    def _populate_tree(self, nodes: tuple[VersionNodeView, ...]) -> None:
        self._tree.clear()
        stack: dict[int, QTreeWidgetItem] = {}
        for node in nodes:
            item = QTreeWidgetItem([node.title, node.status])
            item.setData(0, Qt.ItemDataRole.UserRole, node.node_id)
            if node.depth <= 0:
                self._tree.addTopLevelItem(item)
            else:
                parent = stack.get(node.depth - 1)
                if parent is None:
                    self._tree.addTopLevelItem(item)
                else:
                    parent.addChild(item)
            stack[node.depth] = item
        self._tree.expandAll()

    def _select_first_tree_item(self) -> None:
        first = self._tree.topLevelItem(0)
        if first is None:
            self._render_detail(self._vm.selected_detail())
            return
        self._tree.setCurrentItem(first)
        self._render_detail(self._vm.node_detail(str(first.data(0, Qt.ItemDataRole.UserRole))))

    def _on_tree_selection_changed(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        node_id = str(item.data(0, Qt.ItemDataRole.UserRole))
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

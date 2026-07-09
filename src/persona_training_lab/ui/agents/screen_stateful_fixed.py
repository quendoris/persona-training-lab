from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from persona_training_lab.ui.agents.screen_stateful import AgentsScreen as _StatefulAgentsScreen
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


class AgentsScreen(_StatefulAgentsScreen):
    def __init__(self, view_model) -> None:
        super().__init__(view_model)
        if hasattr(self._graph, "menu_action_requested"):
            self._graph.menu_action_requested.connect(self._handle_canvas_menu_action)

    def _details(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        detail_card = PanelCard("Карточка узла", "Действия открываются ЛКМ по точке прямо на графе.")
        self._detail_title = QLabel("—")
        self._detail_title.setObjectName("CardTitle")
        self._detail_body = QLabel("—")
        self._detail_body.setWordWrap(True)
        detail_card.add_widget(self._detail_title)
        detail_card.add_widget(self._detail_body)
        detail_card.add_widget(QLabel("Проверить"))
        self._checks_layout = QGridLayout()
        detail_card._layout.addLayout(self._checks_layout)
        detail_card.add_widget(QLabel("Справка"))
        self._actions_layout = QGridLayout()
        detail_card._layout.addLayout(self._actions_layout)
        layout.addWidget(detail_card)
        layout.addStretch(1)
        return column

    def _select_node(self, node_id: str) -> None:
        super()._select_node(node_id)

    def _handle_canvas_menu_action(self, node_id: str, action: str) -> None:
        self._select_node(node_id)
        if action == "make_current":
            self._make_current()
        elif action == "mark_good":
            self._mark_tone("good")
        elif action == "mark_pending":
            self._mark_tone("pending")
        elif action == "mark_bad":
            self._mark_tone("bad")
        elif action == "continue":
            self._continue_from_selected()
        elif action == "center":
            self._center_on_node(node_id)
        elif action == "reset_node":
            self._reset_node_layout(node_id)
        elif action == "reset_subtree":
            self._reset_subtree_layout(node_id)

    def _reset_node_layout(self, node_id: str) -> None:
        if hasattr(self._graph, "reset_node_layout"):
            self._graph.reset_node_layout(node_id)
        QTimer.singleShot(0, lambda: self._center_on_node(node_id))

    def _reset_subtree_layout(self, node_id: str) -> None:
        if hasattr(self._graph, "reset_subtree_layout"):
            self._graph.reset_subtree_layout(node_id)
        QTimer.singleShot(0, lambda: self._center_on_node(node_id))

    def _detail_for(self, node_id: str) -> AgentDetailView:
        node = self._node_by_id(node_id)
        if node is None:
            return self._vm.node_detail(node_id)
        if self._state.is_custom_node(node_id):
            return AgentDetailView(
                title=node.title,
                body="\n".join((f"Parent: {node.parent_id or '—'}", f"Статус: {node.status}", node.subtitle)),
                checks=("Локальная ветка lineage", "Пока не связана с training run", "Перед запуском нужен snapshot/protocol record"),
                actions=("ЛКМ по точке открывает действия на графе.", "ПКМ двигает пространство/точку."),
            )
        base = self._vm.node_detail(node_id)
        body = "\n".join((base.body, "", f"Lineage state: {node.status}", f"Parent: {node.parent_id or '—'}"))
        return AgentDetailView(base.title, body, base.checks, ("ЛКМ по точке открывает действия на графе.", "ПКМ двигает пространство/точку."))

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QTimer
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from persona_training_lab.ui.agents.screen_stateful import AgentsScreen as _StatefulAgentsScreen
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


class AgentsScreen(_StatefulAgentsScreen):
    def __init__(self, view_model) -> None:
        self._floating_node_menu: QFrame | None = None
        super().__init__(view_model)
        if hasattr(self._graph, "context_menu_requested"):
            self._graph.context_menu_requested.connect(self._show_node_context_menu)
        if hasattr(self._graph, "context_menu_dismiss_requested"):
            self._graph.context_menu_dismiss_requested.connect(self._hide_node_context_menu)

    def _details(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        workflow_card = PanelCard("Workflow действия", "Кнопки всегда относятся к выбранной точке дерева.")
        self._selected_caption = QLabel("Выбрано: —")
        self._selected_caption.setObjectName("CardTitle")
        workflow_card.add_widget(self._selected_caption)
        self._workflow_status = make_muted_label("Состояние: —")
        workflow_card.add_widget(self._workflow_status)
        self._make_current_button = self._workflow_button("Сделать актуальной", self._make_current)
        self._mark_good_button = self._workflow_button("Пометить удачной", lambda: self._mark_tone("good"))
        self._mark_pending_button = self._workflow_button("Пометить спорной", lambda: self._mark_tone("pending"))
        self._mark_bad_button = self._workflow_button("Пометить неудачной", lambda: self._mark_tone("bad"))
        self._continue_button = self._workflow_button("Продолжить от этой точки", self._continue_from_selected)
        for button in (
            self._make_current_button,
            self._mark_good_button,
            self._mark_pending_button,
            self._mark_bad_button,
            self._continue_button,
        ):
            button.setMinimumHeight(34)
            button.setEnabled(True)
            workflow_card.add_widget(button)
        layout.addWidget(workflow_card)

        detail_card = PanelCard("Карточка узла", "Параметры и справка выбранной точки.")
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
        self._sync_workflow_panel()

    def _show_node_context_menu(self, node_id: str, global_pos: QPointF) -> None:
        self._select_node(node_id)
        self._hide_node_context_menu()
        menu = QFrame(self)
        menu.setObjectName("PanelCardSoft")
        menu.setFrameShape(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(menu)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        title = QLabel("Действия точки")
        title.setObjectName("CardTitle")
        layout.addWidget(title)
        layout.addWidget(make_muted_label(node_id))
        actions: tuple[tuple[str, Callable[[], None]], ...] = (
            ("Сделать актуальной", self._make_current),
            ("Пометить удачной", lambda: self._mark_tone("good")),
            ("Пометить спорной", lambda: self._mark_tone("pending")),
            ("Пометить неудачной", lambda: self._mark_tone("bad")),
            ("Продолжить от этой точки", self._continue_from_selected),
            ("Центрировать на точке", lambda: self._center_on_node(node_id)),
            ("Сбросить смещение точки", lambda: self._reset_node_layout(node_id)),
            ("Сбросить смещение поддерева", lambda: self._reset_subtree_layout(node_id)),
        )
        for text, handler in actions:
            layout.addWidget(self._menu_button(text, handler))
        self._floating_node_menu = menu
        menu.adjustSize()
        pos = self.mapFromGlobal(global_pos.toPoint())
        x = max(8, min(pos.x() + 10, self.width() - menu.width() - 8))
        y = max(8, min(pos.y() + 10, self.height() - menu.height() - 8))
        menu.move(x, y)
        menu.show()
        menu.raise_()

    def _menu_button(self, text: str, handler: Callable[[], None]) -> QPushButton:
        button = self._button(text)
        button.setMinimumHeight(30)
        button.clicked.connect(lambda: self._run_menu_action(handler))
        return button

    def _run_menu_action(self, handler: Callable[[], None]) -> None:
        handler()
        self._hide_node_context_menu()

    def _hide_node_context_menu(self) -> None:
        if self._floating_node_menu is None:
            return
        self._floating_node_menu.hide()
        self._floating_node_menu.deleteLater()
        self._floating_node_menu = None

    def _reset_node_layout(self, node_id: str) -> None:
        if hasattr(self._graph, "reset_node_layout"):
            self._graph.reset_node_layout(node_id)
        QTimer.singleShot(0, lambda: self._center_on_node(node_id))

    def _reset_subtree_layout(self, node_id: str) -> None:
        if hasattr(self._graph, "reset_subtree_layout"):
            self._graph.reset_subtree_layout(node_id)
        QTimer.singleShot(0, lambda: self._center_on_node(node_id))

    def _sync_workflow_panel(self) -> None:
        node = self._node_by_id(self._selected_node_id)
        if node is None:
            self._selected_caption.setText(f"Выбрано: {self._selected_node_id}")
            self._workflow_status.setText("Состояние: —")
            enabled = False
        else:
            self._selected_caption.setText(f"Выбрано: {node.title}")
            self._workflow_status.setText(f"Состояние: {node.status} · tone={node.tone} · parent={node.parent_id or '—'}")
            enabled = True
        for button in (
            self._make_current_button,
            self._mark_good_button,
            self._mark_pending_button,
            self._mark_bad_button,
            self._continue_button,
        ):
            button.setEnabled(enabled)

    def _detail_for(self, node_id: str) -> AgentDetailView:
        node = self._node_by_id(node_id)
        if node is None:
            return self._vm.node_detail(node_id)
        if self._state.is_custom_node(node_id):
            return AgentDetailView(
                title=node.title,
                body="\n".join((f"Parent: {node.parent_id or '—'}", f"Статус: {node.status}", node.subtitle)),
                checks=("Локальная ветка lineage", "Пока не связана с training run", "Перед запуском нужен snapshot/protocol record"),
                actions=("ЛКМ по точке открывает меню, ПКМ перемещает пространство/точки.",),
            )
        base = self._vm.node_detail(node_id)
        body = "\n".join((base.body, "", f"Lineage state: {node.status}", f"Parent: {node.parent_id or '—'}"))
        return AgentDetailView(base.title, body, base.checks, ("ЛКМ по точке открывает меню, ПКМ перемещает пространство/точки.",))

from __future__ import annotations

from PySide6.QtCore import QPointF, QTimer
from PySide6.QtWidgets import QGridLayout, QInputDialog, QLabel, QMessageBox, QVBoxLayout, QWidget

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

    def _on_graph_zoom_anchor(self, anchor: QPointF, old_zoom: float, new_zoom: float) -> None:
        if old_zoom <= 0:
            return
        ratio = new_zoom / old_zoom
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()

        # anchor is in the old canvas coordinate system, not viewport coordinates.
        # Preserve the viewport point under the cursor:
        # new_scroll = old_scroll + (ratio - 1) * canvas_anchor.
        target_h = int(round(hbar.value() + (ratio - 1.0) * anchor.x()))
        target_v = int(round(vbar.value() + (ratio - 1.0) * anchor.y()))
        QTimer.singleShot(0, lambda: self._apply_graph_zoom_scroll(target_h, target_v))

    def _apply_graph_zoom_scroll(self, horizontal: int, vertical: int) -> None:
        self._graph_scroll.horizontalScrollBar().setValue(horizontal)
        self._graph_scroll.verticalScrollBar().setValue(vertical)

    def _handle_canvas_menu_action(self, node_id: str, action: str) -> None:
        self._select_node(node_id)
        self._close_canvas_menu()
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
        elif action == "rename":
            self._rename_local_branch(node_id)
        elif action == "archive_toggle":
            self._toggle_local_branch_archive(node_id)
        elif action == "delete_subtree":
            self._delete_local_branch_subtree(node_id)
        elif action == "center":
            self._center_on_node(node_id)
        elif action == "reset_node":
            self._reset_node_layout(node_id)
        elif action == "reset_subtree":
            self._reset_subtree_layout(node_id)

    def _rename_local_branch(self, node_id: str) -> None:
        node = self._node_by_id(node_id)
        if node is None or not self._state.is_custom_node(node_id):
            return
        title, accepted = QInputDialog.getText(self, "Переименовать ветку", "Новое название:", text=node.title)
        if not accepted or not title.strip():
            return
        if self._state.rename_node(node_id, title):
            self._selected_node_id = node_id
            self._refresh_lineage(center=False)

    def _toggle_local_branch_archive(self, node_id: str) -> None:
        if not self._state.is_custom_node(node_id):
            return
        archived = not self._state.is_archived(node_id)
        if self._state.set_archived(node_id, archived):
            self._selected_node_id = node_id
            self._refresh_lineage(center=False)

    def _delete_local_branch_subtree(self, node_id: str) -> None:
        node = self._node_by_id(node_id)
        removed_ids = self._state.custom_subtree_ids(node_id)
        if node is None or not removed_ids:
            return
        descendants = len(removed_ids) - 1
        detail = "Ветка будет удалена без возможности восстановления."
        if descendants:
            detail = f"Будет удалена эта ветка и дочерние точки: {descendants}."
        answer = QMessageBox.question(
            self,
            "Удалить локальную ветку?",
            f"{node.title}\n\n{detail}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        fallback_id = node.parent_id or self._graph.current_node_id()
        removed = self._state.delete_subtree(node_id)
        if not removed:
            return
        if hasattr(self._graph, "forget_layout_nodes"):
            self._graph.forget_layout_nodes(removed)
        self._selected_node_id = fallback_id
        self._refresh_lineage(center=True)

    def _close_canvas_menu(self) -> None:
        if hasattr(self._graph, "close_node_menu"):
            self._graph.close_node_menu()

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
            archive_state = "Да" if self._state.is_archived(node_id) else "Нет"
            return AgentDetailView(
                title=node.title,
                body="\n".join(
                    (
                        f"Parent: {node.parent_id or '—'}",
                        f"Статус: {node.status}",
                        f"В архиве: {archive_state}",
                        node.subtitle,
                    )
                ),
                checks=("Локальная ветка lineage", "Пока не связана с training run", "Перед запуском нужен snapshot/protocol record"),
                actions=("ЛКМ по точке открывает действия на графе.", "ПКМ двигает пространство/точку."),
            )
        base = self._vm.node_detail(node_id)
        body = "\n".join((base.body, "", f"Lineage state: {node.status}", f"Parent: {node.parent_id or '—'}"))
        return AgentDetailView(base.title, body, base.checks, ("ЛКМ по точке открывает действия на графе.", "ПКМ двигает пространство/точку."))

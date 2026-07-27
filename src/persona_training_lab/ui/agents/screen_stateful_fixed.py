from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QGridLayout, QInputDialog, QLabel, QMessageBox, QVBoxLayout, QWidget

from persona_training_lab.ui.agents.key_bindings import agent_graph_key_bindings_by_id
from persona_training_lab.ui.agents.lineage_state import HistoryTransition
from persona_training_lab.ui.agents.screen_stateful import AgentsScreen as _StatefulAgentsScreen
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


class AgentsScreen(_StatefulAgentsScreen):
    def __init__(self, view_model) -> None:
        super().__init__(view_model)
        if hasattr(self._graph, "menu_action_requested"):
            self._graph.menu_action_requested.connect(self._handle_canvas_menu_action)
        if hasattr(self._graph, "layout_action_committed"):
            self._graph.layout_action_committed.connect(self._record_graph_layout_action)
        self._setup_shortcuts()
        self._sync_history_action()

    def _setup_shortcuts(self) -> None:
        definitions = agent_graph_key_bindings_by_id()
        handlers = {
            "delete_branch": self._delete_selected_local_branch,
            "history_toggle": self._toggle_last_history_action,
            "undo_only": self._undo_history_only,
        }
        self._shortcuts: dict[str, QShortcut] = {}
        for binding_id, handler in handlers.items():
            definition = definitions[binding_id]
            sequence = QKeySequence.fromString(definition.sequence, QKeySequence.SequenceFormat.PortableText)
            shortcut = QShortcut(sequence, self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.setAutoRepeat(definition.auto_repeat)
            shortcut.activated.connect(handler)
            self._shortcuts[binding_id] = shortcut

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

    def _refresh_lineage(self, center: bool) -> None:
        super()._refresh_lineage(center)
        self._sync_history_action()

    def _layout_snapshot(self) -> dict[str, Any]:
        if hasattr(self._graph, "layout_snapshot"):
            snapshot = self._graph.layout_snapshot()
            return snapshot if isinstance(snapshot, dict) else {}
        return {}

    def _make_current(self) -> None:
        self._state.set_current(self._selected_node_id, self._layout_snapshot())
        self._refresh_lineage(center=True)

    def _mark_tone(self, tone: str) -> None:
        self._state.set_tone(self._selected_node_id, tone, self._layout_snapshot())
        self._refresh_lineage(center=False)

    def _continue_from_selected(self) -> None:
        self._selected_node_id = self._state.continue_from(self._selected_node_id, self._layout_snapshot())
        self._refresh_lineage(center=True)

    def _on_graph_zoom_anchor(self, anchor: QPointF, old_zoom: float, new_zoom: float) -> None:
        if old_zoom <= 0:
            return
        ratio = new_zoom / old_zoom
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
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
        elif action == "history_toggle":
            self._toggle_last_history_action()
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

    def _delete_selected_local_branch(self) -> None:
        node_id = self._selected_node_id
        if not self._state.is_custom_node(node_id):
            return
        self._close_canvas_menu()
        self._delete_local_branch_subtree(node_id)

    def _toggle_last_history_action(self) -> None:
        self._close_canvas_menu()
        transition = self._state.quick_toggle(self._layout_snapshot())
        self._apply_history_transition(transition)

    def _undo_history_only(self) -> None:
        self._close_canvas_menu()
        transition = self._state.undo_only(self._layout_snapshot())
        self._apply_history_transition(transition)

    def _undo_last_lineage_action(self) -> None:
        # Compatibility for older callers: this path means strict undo, not toggle.
        self._undo_history_only()

    def _apply_history_transition(self, transition: HistoryTransition | None) -> None:
        if transition is None:
            self._sync_history_action()
            return
        old_selected = self._selected_node_id
        self._lineage_nodes = self._build_nodes()
        node_ids = {node.node_id for node in self._lineage_nodes}
        if self._selected_node_id not in node_ids:
            current_id = self._state.current_node_id()
            if current_id in node_ids:
                self._selected_node_id = current_id
            else:
                current = next((node.node_id for node in self._lineage_nodes if node.is_current), "")
                self._selected_node_id = current or (self._lineage_nodes[0].node_id if self._lineage_nodes else "snapshot")
        self._graph.set_nodes(self._lineage_nodes)
        if hasattr(self._graph, "restore_layout_snapshot"):
            self._graph.restore_layout_snapshot(transition.layout_snapshot)
        self._select_node(self._selected_node_id)
        self._sync_history_action()
        if old_selected != self._selected_node_id:
            QTimer.singleShot(0, lambda: self._center_on_node(self._selected_node_id))

    def _record_graph_layout_action(self, label: str, before_layout: object, critical: bool) -> None:
        if not isinstance(before_layout, dict):
            return
        self._state.record_layout_action(label, before_layout, critical=critical)
        self._sync_history_action()

    def _sync_history_action(self) -> None:
        if hasattr(self._graph, "set_history_action_text"):
            text = self._state.history_toggle_text() if self._state.can_toggle_history() else None
            self._graph.set_history_action_text(text)
            return
        if hasattr(self._graph, "set_undo_action_label"):
            label = self._state.last_action_label() if self._state.can_undo() else None
            self._graph.set_undo_action_label(label)

    def _sync_undo_action(self) -> None:
        self._sync_history_action()

    def _rename_local_branch(self, node_id: str) -> None:
        node = self._node_by_id(node_id)
        if node is None or not self._state.is_custom_node(node_id):
            return
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Переименовать ветку")
        dialog.setLabelText("Новое название:")
        dialog.setTextValue(node.title)
        dialog.setOkButtonText("Сохранить")
        dialog.setCancelButtonText("Отмена")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        title = dialog.textValue().strip()
        if not title:
            return
        if self._state.rename_node(node_id, title, self._layout_snapshot()):
            self._selected_node_id = node_id
            self._refresh_lineage(center=False)

    def _toggle_local_branch_archive(self, node_id: str) -> None:
        if not self._state.is_custom_node(node_id):
            return
        archived = not self._state.is_archived(node_id)
        if self._state.set_archived(node_id, archived, self._layout_snapshot()):
            self._selected_node_id = node_id
            self._refresh_lineage(center=False)

    def _delete_local_branch_subtree(self, node_id: str) -> None:
        node = self._node_by_id(node_id)
        removed_ids = self._state.custom_subtree_ids(node_id)
        if node is None or not removed_ids:
            return
        descendants = len(removed_ids) - 1
        detail = "Ветку можно будет вернуть через защищённую историю действий."
        if descendants:
            detail = f"Будет удалена эта ветка и дочерние точки: {descendants}. Удаление сохранится в защищённой истории."
        if not self._confirm_branch_deletion(node.title, detail):
            return
        fallback_id = node.parent_id or self._graph.current_node_id()
        removed = self._state.delete_subtree(node_id, self._layout_snapshot())
        if not removed:
            return
        if hasattr(self._graph, "forget_layout_nodes"):
            self._graph.forget_layout_nodes(removed)
        self._selected_node_id = fallback_id
        self._refresh_lineage(center=True)

    def _confirm_branch_deletion(self, title: str, detail: str) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Удалить локальную ветку?")
        dialog.setText(f"{title}\n\n{detail}")
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        yes_button = dialog.button(QMessageBox.StandardButton.Yes)
        no_button = dialog.button(QMessageBox.StandardButton.No)
        if yes_button is not None:
            yes_button.setText("Да")
        if no_button is not None:
            no_button.setText("Нет")
        dialog.exec()
        return yes_button is not None and dialog.clickedButton() is yes_button

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
        shortcut_help = (
            "Del удаляет выбранную локальную ветку.",
            "Ctrl+Z переключает последнее изменение: отменить / вернуть.",
            "Ctrl+Shift+Z всегда уходит ещё на один шаг назад и поддерживает удержание.",
        )
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
                actions=("ЛКМ по точке открывает действия на графе.", "ПКМ двигает пространство/точку.", *shortcut_help),
            )
        base = self._vm.node_detail(node_id)
        body = "\n".join((base.body, "", f"Lineage state: {node.status}", f"Parent: {node.parent_id or '—'}"))
        return AgentDetailView(
            base.title,
            body,
            base.checks,
            ("ЛКМ по точке открывает действия на графе.", "ПКМ двигает пространство/точку.", *shortcut_help[1:]),
        )

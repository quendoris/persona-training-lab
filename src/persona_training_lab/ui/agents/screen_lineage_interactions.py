from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.agents.key_bindings import (
    agent_graph_key_bindings_by_id,
)
from persona_training_lab.ui.agents.lineage_state import (
    HISTORY_ACTION_KEYS,
    HistoryTransition,
)
from persona_training_lab.ui.agents.screen_lineage_base import (
    AgentsScreen as _LineageBaseAgentsScreen,
)
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


class AgentsScreen(_LineageBaseAgentsScreen):
    """Own lineage commands, local branch mutation, and state-history effects."""

    def __init__(
        self,
        view_model,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__(view_model, localization)
        if hasattr(self._graph, "menu_action_requested"):
            self._graph.menu_action_requested.connect(
                self._handle_canvas_menu_action
            )
        if hasattr(self._graph, "layout_action_committed"):
            self._graph.layout_action_committed.connect(
                self._record_graph_layout_action
            )
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
            sequence = QKeySequence.fromString(
                definition.sequence,
                QKeySequence.SequenceFormat.PortableText,
            )
            shortcut = QShortcut(sequence, self)
            shortcut.setContext(
                Qt.ShortcutContext.WidgetWithChildrenShortcut
            )
            shortcut.setAutoRepeat(definition.auto_repeat)
            shortcut.activated.connect(handler)
            self._shortcuts[binding_id] = shortcut

    def _details(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        detail_card = PanelCard(
            self._text("agents.details.node_title"),
            self._text("agents.details.node_subtitle"),
        )
        self._details_card = detail_card
        self._detail_title = QLabel("—")
        self._detail_title.setObjectName("CardTitle")
        self._detail_body = QLabel("—")
        self._detail_body.setWordWrap(True)
        detail_card.add_widget(self._detail_title)
        detail_card.add_widget(self._detail_body)
        self._detail_checks_title = QLabel(
            self._text("agents.details.check")
        )
        detail_card.add_widget(self._detail_checks_title)
        self._checks_layout = QGridLayout()
        detail_card._layout.addLayout(self._checks_layout)
        self._detail_help_title = QLabel(
            self._text("agents.details.help")
        )
        detail_card.add_widget(self._detail_help_title)
        self._actions_layout = QGridLayout()
        detail_card._layout.addLayout(self._actions_layout)
        layout.addWidget(detail_card)
        layout.addStretch(1)
        return column

    def _refresh_lineage(self, center: bool) -> None:
        super()._refresh_lineage(center)
        self._sync_history_action()

    def _layout_snapshot(self) -> dict[str, Any]:
        if hasattr(self._graph, "layout_snapshot"):
            snapshot = self._graph.layout_snapshot()
            return snapshot if isinstance(snapshot, dict) else {}
        return {}

    def _make_current(self) -> None:
        self._state.set_current(
            self._selected_node_id,
            self._layout_snapshot(),
        )
        self._refresh_lineage(center=True)

    def _mark_tone(self, tone: str) -> None:
        self._state.set_tone(
            self._selected_node_id,
            tone,
            self._layout_snapshot(),
        )
        self._refresh_lineage(center=False)

    def _continue_from_selected(self) -> None:
        self._selected_node_id = self._state.continue_from(
            self._selected_node_id,
            self._layout_snapshot(),
        )
        self._refresh_lineage(center=True)

    def _on_graph_zoom_anchor(
        self,
        anchor: QPointF,
        old_zoom: float,
        new_zoom: float,
    ) -> None:
        if old_zoom <= 0:
            return
        ratio = new_zoom / old_zoom
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        target_h = int(
            round(hbar.value() + (ratio - 1.0) * anchor.x())
        )
        target_v = int(
            round(vbar.value() + (ratio - 1.0) * anchor.y())
        )
        QTimer.singleShot(
            0,
            lambda: self._apply_graph_zoom_scroll(
                target_h,
                target_v,
            ),
        )

    def _apply_graph_zoom_scroll(
        self,
        horizontal: int,
        vertical: int,
    ) -> None:
        self._graph_scroll.horizontalScrollBar().setValue(horizontal)
        self._graph_scroll.verticalScrollBar().setValue(vertical)

    def _handle_canvas_menu_action(
        self,
        node_id: str,
        action: str,
    ) -> None:
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
        transition = self._state.quick_toggle(
            self._layout_snapshot()
        )
        self._apply_history_transition(transition)

    def _undo_history_only(self) -> None:
        self._close_canvas_menu()
        transition = self._state.undo_only(
            self._layout_snapshot()
        )
        self._apply_history_transition(transition)

    def _undo_last_lineage_action(self) -> None:
        # Compatibility for older callers: this path means strict undo, not toggle.
        self._undo_history_only()

    def _apply_history_transition(
        self,
        transition: HistoryTransition | None,
    ) -> None:
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
                current = next(
                    (
                        node.node_id
                        for node in self._lineage_nodes
                        if node.is_current
                    ),
                    "",
                )
                self._selected_node_id = current or (
                    self._lineage_nodes[0].node_id
                    if self._lineage_nodes
                    else "snapshot"
                )
        self._graph.set_nodes(self._lineage_nodes)
        if hasattr(self._graph, "restore_layout_snapshot"):
            self._graph.restore_layout_snapshot(
                transition.layout_snapshot
            )
        self._select_node(self._selected_node_id)
        self._sync_history_action()
        if old_selected != self._selected_node_id:
            QTimer.singleShot(
                0,
                lambda: self._center_on_node(
                    self._selected_node_id
                ),
            )

    def _record_graph_layout_action(
        self,
        action_code: str,
        before_layout: object,
        critical: bool,
    ) -> None:
        if not isinstance(before_layout, dict):
            return
        self._state.record_layout_action(
            action_code,
            before_layout,
            critical=critical,
        )
        self._sync_history_action()

    def _history_action_label(self, action_code: str) -> str:
        key = HISTORY_ACTION_KEYS.get(action_code)
        return self._text(key) if key is not None else action_code

    def _sync_history_action(self) -> None:
        if hasattr(self._graph, "set_history_action_text"):
            parts = self._state.history_toggle_parts()
            text = None
            if parts is not None:
                direction, action_code = parts
                text = self._text(
                    "agents.history.redo"
                    if direction == "redo"
                    else "agents.history.undo",
                    action=self._history_action_label(action_code),
                )
            self._graph.set_history_action_text(text)
            return
        if hasattr(self._graph, "set_undo_action_label"):
            action_code = self._state.last_action_code()
            label = (
                self._history_action_label(action_code)
                if action_code
                else None
            )
            self._graph.set_undo_action_label(label)

    def _sync_undo_action(self) -> None:
        self._sync_history_action()

    def _rename_local_branch(self, node_id: str) -> None:
        node = self._node_by_id(node_id)
        if node is None or not self._state.is_custom_node(node_id):
            return
        dialog = QInputDialog(self)

        def refresh_dialog(_locale: str = "") -> None:
            dialog.setWindowTitle(
                self._text("agents.dialog.rename.title")
            )
            dialog.setLabelText(
                self._text("agents.dialog.rename.label")
            )
            dialog.setOkButtonText(self._text("common.save"))
            dialog.setCancelButtonText(self._text("common.cancel"))

        refresh_dialog()
        dialog.setTextValue(self._render_text(node.title))
        localization = self._localization
        if localization is not None:
            localization.language_changed.connect(refresh_dialog)
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
        finally:
            if localization is not None:
                try:
                    localization.language_changed.disconnect(refresh_dialog)
                except (RuntimeError, TypeError):
                    pass
        if not accepted:
            return
        title = dialog.textValue().strip()
        if not title:
            return
        if self._state.rename_node(
            node_id,
            title,
            self._layout_snapshot(),
        ):
            self._selected_node_id = node_id
            self._refresh_lineage(center=False)

    def _toggle_local_branch_archive(self, node_id: str) -> None:
        if not self._state.is_custom_node(node_id):
            return
        archived = not self._state.is_archived(node_id)
        if self._state.set_archived(
            node_id,
            archived,
            self._layout_snapshot(),
        ):
            self._selected_node_id = node_id
            self._refresh_lineage(center=False)

    def _delete_local_branch_subtree(self, node_id: str) -> None:
        node = self._node_by_id(node_id)
        removed_ids = self._state.custom_subtree_ids(node_id)
        if node is None or not removed_ids:
            return
        descendants = len(removed_ids) - 1
        detail = self._text("agents.dialog.delete.single")
        if descendants:
            detail = self._text(
                "agents.dialog.delete.subtree",
                count=descendants,
            )
        if not self._confirm_branch_deletion(
            self._render_text(node.title),
            detail,
        ):
            return
        fallback_id = node.parent_id or self._graph.current_node_id()
        removed = self._state.delete_subtree(
            node_id,
            self._layout_snapshot(),
        )
        if not removed:
            return
        if hasattr(self._graph, "forget_layout_nodes"):
            self._graph.forget_layout_nodes(removed)
        self._selected_node_id = fallback_id
        self._refresh_lineage(center=True)

    def _confirm_branch_deletion(
        self,
        title: str,
        detail: str,
    ) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setText(f"{title}\n\n{detail}")
        dialog.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        yes_button = dialog.button(QMessageBox.StandardButton.Yes)
        no_button = dialog.button(QMessageBox.StandardButton.No)

        def refresh_dialog(_locale: str = "") -> None:
            dialog.setWindowTitle(
                self._text("agents.dialog.delete.title")
            )
            if yes_button is not None:
                yes_button.setText(self._text("common.yes"))
            if no_button is not None:
                no_button.setText(self._text("common.no"))

        refresh_dialog()
        localization = self._localization
        if localization is not None:
            localization.language_changed.connect(refresh_dialog)
        try:
            dialog.exec()
        finally:
            if localization is not None:
                try:
                    localization.language_changed.disconnect(refresh_dialog)
                except (RuntimeError, TypeError):
                    pass
        return (
            yes_button is not None
            and dialog.clickedButton() is yes_button
        )

    def _close_canvas_menu(self) -> None:
        if hasattr(self._graph, "close_node_menu"):
            self._graph.close_node_menu()

    def _reset_node_layout(self, node_id: str) -> None:
        if hasattr(self._graph, "reset_node_layout"):
            self._graph.reset_node_layout(node_id)
        QTimer.singleShot(
            0,
            lambda: self._center_on_node(node_id),
        )

    def _reset_subtree_layout(self, node_id: str) -> None:
        if hasattr(self._graph, "reset_subtree_layout"):
            self._graph.reset_subtree_layout(node_id)
        QTimer.singleShot(
            0,
            lambda: self._center_on_node(node_id),
        )

    def _detail_for(self, node_id: str) -> AgentDetailView:
        node = self._node_by_id(node_id)
        if node is None:
            return self._vm.node_detail(node_id)
        base = self._vm.node_detail(node_id)
        if self._state.is_custom_node(node_id):
            return AgentDetailView(
                title=node.title,
                body=UserMessage(
                    "agents.custom.body",
                    {
                        "parent": node.parent_id or "—",
                        "status": self._render_text(node.status),
                        "archived": self._text(
                            "common.yes"
                            if self._state.is_archived(node_id)
                            else "common.no"
                        ),
                        "subtitle": self._render_text(node.subtitle),
                    },
                ),
                checks=(
                    UserMessage("agents.custom.check.local"),
                    UserMessage("agents.custom.check.training"),
                    UserMessage("agents.custom.check.snapshot"),
                ),
                actions=(),
                action_codes=(
                    "open_actions",
                    "pan",
                    "delete",
                    "toggle",
                    "undo",
                ),
            )
        return AgentDetailView(
            title=base.title,
            body=base.body,
            checks=base.checks,
            actions=base.actions,
            action_codes=(
                *base.action_codes,
                "open_actions",
                "pan",
                "toggle",
                "undo",
            ),
        )

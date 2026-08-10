from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.agents.screen_history_keyguard import (
    AgentsScreen as _HistoryKeyGuardAgentsScreen,
)
from persona_training_lab.ui.agents.screen_lineage_base import (
    AgentsScreen as _LineageBaseAgentsScreen,
)
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import (
    make_muted_label,
    make_status_label,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentDetailView,
    AgentText,
)


class AgentsScreen(_HistoryKeyGuardAgentsScreen):
    """Own bounded Agents workspace presentation and detail rendering."""

    _ROLES_MIN_WIDTH = 300
    _ROLES_MAX_WIDTH = 390
    _DETAILS_MIN_WIDTH = 390
    _DETAILS_MAX_WIDTH = 560

    def __init__(
        self,
        view_model,
        key_binding_manager: KeyBindingManager | None = None,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__(
            view_model,
            key_binding_manager,
            localization,
        )
        self.setMinimumSize(0, 0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        if hasattr(self._graph, "set_input_bindings"):
            self._graph.set_input_bindings(self._key_binding_manager)
        self._key_binding_manager.bindings_changed.connect(
            self._refresh_key_binding_help
        )

    def _roles(self) -> QWidget:
        content = _LineageBaseAgentsScreen._roles(self)
        self._roles_content = content
        return self._bounded_column_scroll(
            content,
            object_name="AgentsRolesScroll",
            minimum_width=self._ROLES_MIN_WIDTH,
            maximum_width=self._ROLES_MAX_WIDTH,
        )

    def _details(self) -> QWidget:
        content = QWidget()
        content.setProperty("transparentBg", True)
        content.setMinimumSize(0, 0)
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        card = PanelCard(
            self._text("agents.details.version_title"),
            self._text("agents.details.version_subtitle"),
        )
        self._details_card = card

        heading = QHBoxLayout()
        heading.setSpacing(10)
        self._detail_title = QLabel("—")
        self._detail_title.setObjectName("SectionTitle")
        self._detail_title.setWordWrap(True)
        self._detail_status = make_status_label("—")
        heading.addWidget(self._detail_title, 1)
        heading.addWidget(
            self._detail_status,
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        card._layout.addLayout(heading)

        metadata = QGridLayout()
        metadata.setHorizontalSpacing(12)
        metadata.setVerticalSpacing(7)
        self._metadata_labels: dict[str, QLabel] = {}
        self._detail_type_value = self._metadata_row(
            metadata,
            0,
            "type",
            "agents.metadata.type",
        )
        self._detail_parent_value = self._metadata_row(
            metadata,
            1,
            "parent",
            "agents.metadata.parent",
        )
        self._detail_branch_value = self._metadata_row(
            metadata,
            2,
            "branch",
            "agents.metadata.branch",
        )
        card._layout.addLayout(metadata)

        self._detail_body = QLabel(
            self._text("agents.details.select_node")
        )
        self._detail_body.setWordWrap(True)
        self._detail_body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        card.add_widget(self._detail_body)

        dependency_frame = QFrame()
        dependency_frame.setObjectName("WarningBlock")
        dependency_layout = QVBoxLayout(dependency_frame)
        dependency_layout.setContentsMargins(12, 10, 12, 10)
        dependency_layout.setSpacing(4)
        self._dependency_title = QLabel(
            self._text("agents.details.dependencies")
        )
        self._dependency_title.setObjectName("CardTitle")
        self._detail_dependency = make_muted_label("—")
        dependency_layout.addWidget(self._dependency_title)
        dependency_layout.addWidget(self._detail_dependency)
        card.add_widget(dependency_frame)

        self._detail_checks_title = QLabel(
            self._text("agents.details.preflight")
        )
        self._detail_checks_title.setObjectName("CardTitle")
        card.add_widget(self._detail_checks_title)
        self._checks_layout = QGridLayout()
        self._checks_layout.setSpacing(8)
        card._layout.addLayout(self._checks_layout)

        self._version_actions_title = QLabel(
            self._text("agents.details.version_actions")
        )
        self._version_actions_title.setObjectName("CardTitle")
        card.add_widget(self._version_actions_title)
        self._workflow_actions_layout = QGridLayout()
        self._workflow_actions_layout.setSpacing(8)
        card._layout.addLayout(self._workflow_actions_layout)

        self._make_current_action = self._version_action_button(
            "agents.action.make_current",
            self._make_current_from_detail,
        )
        self._compare_action = self._version_action_button(
            "agents.action.compare",
            lambda: self._open_workspace("analysis"),
            secondary=True,
        )
        self._portrait_action = self._version_action_button(
            "agents.action.portrait",
            lambda: self._open_workspace("tests"),
        )
        self._branch_action = self._version_action_button(
            "agents.action.branch",
            self._create_branch_from_detail,
            secondary=True,
        )
        self._delete_action = self._version_action_button(
            "agents.action.delete",
            self._delete_branch_from_detail,
            secondary=True,
        )
        self._version_action_keys = {
            self._make_current_action: "agents.action.make_current",
            self._compare_action: "agents.action.compare",
            self._portrait_action: "agents.action.portrait",
            self._branch_action: "agents.action.branch",
            self._delete_action: "agents.action.delete",
        }
        for index, button in enumerate(
            (
                self._make_current_action,
                self._compare_action,
                self._portrait_action,
                self._branch_action,
                self._delete_action,
            )
        ):
            self._workflow_actions_layout.addWidget(
                button,
                index // 2,
                index % 2,
            )

        self._detail_help_title = QLabel(
            self._text("agents.details.context")
        )
        self._detail_help_title.setObjectName("CardTitle")
        card.add_widget(self._detail_help_title)
        self._actions_layout = QGridLayout()
        self._actions_layout.setSpacing(8)
        card._layout.addLayout(self._actions_layout)

        layout.addWidget(card)
        layout.addStretch(1)
        self._details_content = content
        self._constrain_text_widgets(content)
        return self._bounded_column_scroll(
            content,
            object_name="AgentsDetailsScroll",
            minimum_width=self._DETAILS_MIN_WIDTH,
            maximum_width=self._DETAILS_MAX_WIDTH,
        )

    def _metadata_row(
        self,
        layout: QGridLayout,
        row: int,
        metadata_id: str,
        title_key: str,
    ) -> QLabel:
        title_label = QLabel(self._text(title_key))
        title_label.setObjectName("CardTitle")
        self._metadata_labels[metadata_id] = title_label
        value = QLabel("—")
        value.setObjectName("MutedText")
        value.setWordWrap(True)
        value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(
            title_label,
            row,
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        layout.addWidget(value, row, 1)
        return value

    def _version_action_button(
        self,
        text_key: str,
        handler,
        *,
        secondary: bool = False,
    ) -> QPushButton:
        button = QPushButton(self._text(text_key))
        if secondary:
            button.setObjectName("SecondaryButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(34)
        button.clicked.connect(handler)
        return button

    def _graph_panel(self) -> QWidget:
        panel = _LineageBaseAgentsScreen._graph_panel(self)
        panel.setMinimumSize(0, 0)
        panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        return panel

    def _mouse_binding_text(self, binding_id: str) -> str:
        binding = self._key_binding_manager.mouse_binding(binding_id)
        button = self._text(
            f"keybindings.mouse.button.{binding.button}"
        )
        if binding.modifier == "none":
            return button
        modifier = self._text(
            f"keybindings.mouse.modifier.{binding.modifier}"
        )
        return f"{modifier} + {button}"

    def _with_key_binding_help(
        self,
        detail: AgentDetailView,
    ) -> AgentDetailView:
        current = {
            "delete": self._key_binding_manager.sequence(
                "delete_branch"
            ),
            "toggle": self._key_binding_manager.sequence(
                "history_toggle"
            ),
            "undo": self._key_binding_manager.sequence("undo_only"),
            "open": self._mouse_binding_text("open_node_menu"),
            "pan_primary": self._mouse_binding_text(
                "pan_canvas_primary"
            ),
            "pan_secondary": self._mouse_binding_text(
                "pan_canvas_secondary"
            ),
            "move": self._mouse_binding_text("move_node"),
            "subtree": self._mouse_binding_text("move_subtree"),
            "zoom": self._mouse_binding_text("zoom_canvas"),
        }
        actions: list[AgentText] = list(detail.actions)
        for code in dict.fromkeys(detail.action_codes):
            if code == "delete":
                actions.append(
                    UserMessage(
                        "agents.help.delete",
                        {"binding": current["delete"]},
                    )
                )
            elif code == "toggle":
                actions.append(
                    UserMessage(
                        "agents.help.toggle",
                        {"binding": current["toggle"]},
                    )
                )
            elif code == "undo":
                actions.append(
                    UserMessage(
                        "agents.help.undo",
                        {"binding": current["undo"]},
                    )
                )
            elif code == "open_actions":
                actions.append(
                    UserMessage(
                        "agents.help.open_actions",
                        {"binding": current["open"]},
                    )
                )
            elif code == "pan":
                actions.extend(
                    (
                        UserMessage(
                            "agents.help.pan",
                            {
                                "primary": current["pan_primary"],
                                "secondary": current["pan_secondary"],
                            },
                        ),
                        UserMessage(
                            "agents.help.move_node",
                            {"binding": current["move"]},
                        ),
                        UserMessage(
                            "agents.help.move_subtree",
                            {"binding": current["subtree"]},
                        ),
                        UserMessage(
                            "agents.help.zoom",
                            {"binding": current["zoom"]},
                        ),
                    )
                )
        return AgentDetailView(
            title=detail.title,
            body=detail.body,
            checks=detail.checks,
            actions=tuple(actions),
            action_codes=detail.action_codes,
        )

    def _detail_for(self, node_id: str) -> AgentDetailView:
        return self._with_key_binding_help(
            super()._detail_for(node_id)
        )

    def _refresh_key_binding_help(self) -> None:
        node_id = getattr(self, "_selected_node_id", "")
        if node_id:
            self._select_node(node_id)

    def _render_detail(self, detail: AgentDetailView) -> None:
        node_id = getattr(self, "_selected_node_id", "")
        node = self._node_by_id(node_id) if node_id else None
        self._detail_title.setText(self._render_text(detail.title))
        self._detail_body.setText(self._render_text(detail.body))

        if node is None:
            self._set_status(
                self._text("agents.status.undefined"),
                warning=True,
            )
            self._detail_type_value.setText(
                self._text("agents.node.kind.unknown")
            )
            self._detail_parent_value.setText("—")
            self._detail_branch_value.setText("—")
            self._detail_dependency.setText(
                self._text("agents.detail.unknown.body")
            )
            self._sync_detail_actions(
                node_id,
                is_custom=False,
                is_current=False,
                is_archived=False,
            )
        else:
            is_custom = self._state.is_custom_node(node.node_id)
            is_current = bool(
                node.is_current
                or self._state.current_node_id() == node.node_id
            )
            is_archived = bool(
                is_custom and self._state.is_archived(node.node_id)
            )
            status_text = self._version_status_text(
                node.status,
                is_current=is_current,
                is_archived=is_archived,
            )
            warning = is_archived or node.tone in {"pending", "bad"}
            self._set_status(status_text, warning=warning)
            self._detail_type_value.setText(
                self._node_type_label(
                    node.node_id,
                    is_custom=is_custom,
                )
            )
            self._detail_parent_value.setText(
                self._parent_title(node.parent_id)
            )
            self._detail_branch_value.setText(
                self._branch_label(
                    node.branch_note,
                    is_current=is_current,
                    is_archived=is_archived,
                )
            )
            self._detail_dependency.setText(
                self._dependency_text(
                    node.node_id,
                    is_custom=is_custom,
                    is_current=is_current,
                    is_archived=is_archived,
                )
            )
            self._sync_detail_actions(
                node.node_id,
                is_custom=is_custom,
                is_current=is_current,
                is_archived=is_archived,
            )

        self._fill_information_rows(
            self._checks_layout,
            detail.checks,
            "✓",
        )
        self._fill_information_rows(
            self._actions_layout,
            detail.actions,
            "→",
        )
        content = getattr(self, "_details_content", None)
        if content is not None:
            self._constrain_text_widgets(content)

    def _fill_information_rows(
        self,
        layout: QGridLayout,
        values: tuple[AgentText, ...],
        prefix: str,
    ) -> None:
        self._clear_layout(layout)
        effective: tuple[AgentText, ...] = values or (
            UserMessage("agents.details.no_data"),
        )
        for index, value in enumerate(effective):
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(8)
            marker = QLabel(prefix)
            marker.setObjectName("CardTitle")
            text = make_muted_label(self._render_text(value))
            row_layout.addWidget(
                marker,
                0,
                Qt.AlignmentFlag.AlignTop,
            )
            row_layout.addWidget(text, 1)
            layout.addWidget(row, index, 0)

    def _set_status(self, text: str, *, warning: bool) -> None:
        self._detail_status.setText(text)
        self._detail_status.setObjectName(
            "StatusWarning" if warning else "StatusSuccess"
        )
        style = self._detail_status.style()
        style.unpolish(self._detail_status)
        style.polish(self._detail_status)
        self._detail_status.update()

    def _parent_title(self, parent_id: str | None) -> str:
        if parent_id is None:
            return self._text("agents.parent.root")
        parent = self._node_by_id(parent_id)
        if parent is None:
            return parent_id
        return self._display_node_title(parent.title)

    def _display_node_title(self, title: AgentText) -> str:
        rendered = self._render_text(title)
        for prefix in (
            "Base · ",
            "Dataset · ",
            "Train · ",
            "Version · ",
            "Portrait · ",
            "Delta · ",
        ):
            if rendered.startswith(prefix):
                return rendered.removeprefix(prefix)
        return rendered

    def _node_type_label(
        self,
        node_id: str,
        *,
        is_custom: bool,
    ) -> str:
        if is_custom:
            return self._text("agents.node.kind.local_branch")
        key = {
            "base": "agents.node.kind.base_model",
            "dataset": "agents.node.kind.dataset",
            "training": "agents.node.kind.training_run",
            "snapshot": "agents.node.kind.model_version",
            "portrait": "agents.node.kind.evaluation_run",
            "delta": "agents.node.kind.analysis_delta",
        }.get(node_id, "agents.node.kind.lineage")
        return self._text(key)

    def _version_status_text(
        self,
        status: AgentText,
        *,
        is_current: bool,
        is_archived: bool,
    ) -> str:
        if is_current:
            return self._text("agents.status.current")
        if is_archived:
            return self._text("agents.status.archived")
        rendered = self._render_text(status).strip()
        return rendered or self._text("agents.status.no_status")

    def _branch_label(
        self,
        branch_note: str,
        *,
        is_current: bool,
        is_archived: bool,
    ) -> str:
        if is_current:
            return self._text("agents.branch.current")
        if is_archived:
            return self._text("agents.branch.archived")
        if branch_note == "side":
            return self._text("agents.branch.side")
        return self._text("agents.branch.main")

    def _dependency_text(
        self,
        node_id: str,
        *,
        is_custom: bool,
        is_current: bool,
        is_archived: bool,
    ) -> str:
        if is_current:
            return self._text("agents.dependency.current")
        if is_archived:
            return self._text("agents.dependency.archived")
        if is_custom:
            return self._text("agents.dependency.custom")
        key = {
            "base": "agents.dependency.base",
            "dataset": "agents.dependency.dataset",
            "training": "agents.dependency.training",
            "snapshot": "agents.dependency.snapshot",
            "portrait": "agents.dependency.portrait",
            "delta": "agents.dependency.delta",
        }.get(node_id, "agents.dependency.default")
        return self._text(key)

    @staticmethod
    def _detail_capabilities(
        node_id: str,
        *,
        is_custom: bool,
        is_current: bool,
        is_archived: bool,
    ) -> dict[str, bool]:
        is_version = node_id == "snapshot" or is_custom
        return {
            "make_current": (
                is_version and not is_current and not is_archived
            ),
            "compare": is_version and not is_current,
            "portrait": is_version,
            "branch": bool(node_id) and not is_archived,
            "delete": is_custom and not is_current,
        }

    def _sync_detail_actions(
        self,
        node_id: str,
        *,
        is_custom: bool,
        is_current: bool,
        is_archived: bool,
    ) -> None:
        capabilities = self._detail_capabilities(
            node_id,
            is_custom=is_custom,
            is_current=is_current,
            is_archived=is_archived,
        )
        self._make_current_action.setEnabled(
            capabilities["make_current"]
        )
        self._compare_action.setEnabled(capabilities["compare"])
        self._portrait_action.setEnabled(capabilities["portrait"])
        self._branch_action.setEnabled(capabilities["branch"])
        self._delete_action.setEnabled(capabilities["delete"])

        self._make_current_action.setToolTip(
            self._text(
                "agents.action.make_current.current"
                if is_current
                else (
                    "agents.action.make_current.archived"
                    if is_archived
                    else "agents.action.make_current.ready"
                )
            )
        )
        self._compare_action.setToolTip(
            self._text(
                "agents.action.compare.current"
                if is_current
                else "agents.action.compare.ready"
            )
        )
        self._portrait_action.setToolTip(
            self._text("agents.action.portrait.tooltip")
        )
        self._branch_action.setToolTip(
            self._text(
                "agents.action.branch.archived"
                if is_archived
                else "agents.action.branch.ready"
            )
        )
        self._delete_action.setToolTip(
            self._text("agents.action.delete.tooltip")
        )

    def _make_current_from_detail(self) -> None:
        self._make_current()

    def _create_branch_from_detail(self) -> None:
        self._continue_from_selected()

    def _delete_branch_from_detail(self) -> None:
        node_id = getattr(self, "_selected_node_id", "")
        if node_id:
            self._delete_local_branch_subtree(node_id)

    def _open_workspace(self, workspace_key: str) -> None:
        window = self.window()
        navigator = getattr(window, "_go_to_screen", None)
        if callable(navigator):
            navigator(workspace_key)

    def _refresh_presentation_language(self) -> None:
        self._refresh_base_language()
        card = getattr(self, "_details_card", None)
        if card is not None:
            card.set_title(
                self._text("agents.details.version_title")
            )
            card.set_subtitle(
                self._text("agents.details.version_subtitle")
            )
        for metadata_id, key in (
            ("type", "agents.metadata.type"),
            ("parent", "agents.metadata.parent"),
            ("branch", "agents.metadata.branch"),
        ):
            label = self._metadata_labels.get(metadata_id)
            if label is not None:
                label.setText(self._text(key))
        self._dependency_title.setText(
            self._text("agents.details.dependencies")
        )
        self._detail_checks_title.setText(
            self._text("agents.details.preflight")
        )
        self._version_actions_title.setText(
            self._text("agents.details.version_actions")
        )
        self._detail_help_title.setText(
            self._text("agents.details.context")
        )
        for button, key in self._version_action_keys.items():
            button.setText(self._text(key))
        self._sync_history_action()
        node_id = getattr(self, "_selected_node_id", "")
        if node_id:
            self._select_node(node_id)
        self._constrain_text_widgets(self._details_content)

    @staticmethod
    def _bounded_column_scroll(
        content: QWidget,
        *,
        object_name: str,
        minimum_width: int,
        maximum_width: int,
    ) -> QScrollArea:
        content.setMinimumSize(0, 0)
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        scroll = QScrollArea()
        scroll.setObjectName(object_name)
        scroll.setProperty("transparentBg", True)
        scroll.setWidgetResizable(True)
        scroll.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored
        )
        scroll.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        scroll.setMinimumWidth(minimum_width)
        scroll.setMaximumWidth(maximum_width)
        scroll.setMinimumHeight(0)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        scroll.setWidget(content)
        scroll.viewport().setMinimumSize(0, 0)
        scroll.viewport().setProperty("transparentBg", True)
        return scroll

    @staticmethod
    def _constrain_text_widgets(root: QWidget) -> None:
        for label in root.findChildren(QLabel):
            label.setMinimumWidth(0)
            label.setWordWrap(True)
            label.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred,
            )
            if label.text() and not label.toolTip():
                label.setToolTip(label.text())

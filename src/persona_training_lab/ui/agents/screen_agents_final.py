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

from persona_training_lab.ui.agents.screen_history_keyguard import (
    AgentsScreen as _HistoryKeyGuardAgentsScreen,
)
from persona_training_lab.ui.agents.screen_stateful import AgentsScreen as _StatefulAgentsScreen
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


class AgentsScreen(_HistoryKeyGuardAgentsScreen):
    """Final bounded agents layout on top of the stable interaction screen."""

    _ROLES_MIN_WIDTH = 300
    _ROLES_MAX_WIDTH = 390
    _DETAILS_MIN_WIDTH = 390
    _DETAILS_MAX_WIDTH = 560

    def __init__(
        self,
        view_model,
        key_binding_manager: KeyBindingManager | None = None,
    ) -> None:
        super().__init__(view_model, key_binding_manager)
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
        content = _StatefulAgentsScreen._roles(self)
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
            "Карточка версии",
            "Выбранная точка, её происхождение, состояние и безопасные действия.",
        )

        heading = QHBoxLayout()
        heading.setSpacing(10)
        self._detail_title = QLabel("—")
        self._detail_title.setObjectName("SectionTitle")
        self._detail_title.setWordWrap(True)
        self._detail_status = make_status_label("—")
        heading.addWidget(self._detail_title, 1)
        heading.addWidget(self._detail_status, 0, Qt.AlignmentFlag.AlignTop)
        card._layout.addLayout(heading)

        metadata = QGridLayout()
        metadata.setHorizontalSpacing(12)
        metadata.setVerticalSpacing(7)
        self._detail_type_value = self._metadata_row(metadata, 0, "Тип")
        self._detail_parent_value = self._metadata_row(metadata, 1, "Родитель")
        self._detail_branch_value = self._metadata_row(metadata, 2, "Ветка")
        card._layout.addLayout(metadata)

        self._detail_body = QLabel("Выберите точку дерева.")
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
        dependency_title = QLabel("Зависимости и безопасность")
        dependency_title.setObjectName("CardTitle")
        self._detail_dependency = make_muted_label("—")
        dependency_layout.addWidget(dependency_title)
        dependency_layout.addWidget(self._detail_dependency)
        card.add_widget(dependency_frame)

        checks_title = QLabel("Проверить перед действием")
        checks_title.setObjectName("CardTitle")
        card.add_widget(checks_title)
        self._checks_layout = QGridLayout()
        self._checks_layout.setSpacing(8)
        card._layout.addLayout(self._checks_layout)

        actions_title = QLabel("Действия с версией")
        actions_title.setObjectName("CardTitle")
        card.add_widget(actions_title)
        self._workflow_actions_layout = QGridLayout()
        self._workflow_actions_layout.setSpacing(8)
        card._layout.addLayout(self._workflow_actions_layout)

        self._make_current_action = self._version_action_button(
            "Сделать актуальной",
            self._make_current_from_detail,
        )
        self._compare_action = self._version_action_button(
            "Сравнить с текущей",
            lambda: self._open_workspace("analysis"),
            secondary=True,
        )
        self._portrait_action = self._version_action_button(
            "Запустить портрет",
            lambda: self._open_workspace("tests"),
        )
        self._branch_action = self._version_action_button(
            "Создать ветку",
            self._create_branch_from_detail,
            secondary=True,
        )
        self._delete_action = self._version_action_button(
            "Удалить ветку",
            self._delete_branch_from_detail,
            secondary=True,
        )
        for index, button in enumerate(
            (
                self._make_current_action,
                self._compare_action,
                self._portrait_action,
                self._branch_action,
                self._delete_action,
            )
        ):
            self._workflow_actions_layout.addWidget(button, index // 2, index % 2)

        help_title = QLabel("Контекст и управление")
        help_title.setObjectName("CardTitle")
        card.add_widget(help_title)
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

    @staticmethod
    def _metadata_row(layout: QGridLayout, row: int, title: str) -> QLabel:
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        value = QLabel("—")
        value.setObjectName("MutedText")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(title_label, row, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(value, row, 1)
        return value

    @staticmethod
    def _version_action_button(
        text: str,
        handler,
        *,
        secondary: bool = False,
    ) -> QPushButton:
        button = QPushButton(text)
        if secondary:
            button.setObjectName("SecondaryButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(34)
        button.clicked.connect(handler)
        return button

    def _graph_panel(self) -> QWidget:
        panel = _StatefulAgentsScreen._graph_panel(self)
        panel.setMinimumSize(0, 0)
        panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        return panel

    def _detail_for(self, node_id: str) -> AgentDetailView:
        detail = super()._detail_for(node_id)
        current = {
            "delete": self._key_binding_manager.sequence("delete_branch"),
            "toggle": self._key_binding_manager.sequence("history_toggle"),
            "undo": self._key_binding_manager.sequence("undo_only"),
            "open": self._key_binding_manager.mouse_binding_text(
                "open_node_menu"
            ),
            "pan_primary": self._key_binding_manager.mouse_binding_text(
                "pan_canvas_primary"
            ),
            "pan_secondary": self._key_binding_manager.mouse_binding_text(
                "pan_canvas_secondary"
            ),
            "move": self._key_binding_manager.mouse_binding_text("move_node"),
            "subtree": self._key_binding_manager.mouse_binding_text(
                "move_subtree"
            ),
            "zoom": self._key_binding_manager.mouse_binding_text(
                "zoom_canvas"
            ),
        }
        actions: list[str] = []
        for action in detail.actions:
            if action.startswith("Del удаляет"):
                actions.append(
                    f"{current['delete']} удаляет выбранную локальную ветку."
                )
            elif action.startswith("Ctrl+Z переключает"):
                actions.append(
                    f"{current['toggle']} переключает последнее изменение: отменить / вернуть."
                )
            elif action.startswith("Ctrl+Shift+Z всегда"):
                actions.append(
                    f"{current['undo']} всегда уходит ещё на один шаг назад и поддерживает удержание."
                )
            elif action.startswith("ЛКМ по точке"):
                actions.append(
                    f"{current['open']} по точке открывает действия на графе."
                )
            elif action.startswith("ПКМ двигает пространство/точку"):
                actions.extend(
                    (
                        f"{current['pan_primary']} или {current['pan_secondary']} по пустому месту перемещает пространство.",
                        f"{current['move']} по точке перемещает один узел.",
                        f"{current['subtree']} по точке перемещает поддерево.",
                        f"{current['zoom']} масштабирует граф.",
                    )
                )
            else:
                actions.append(action)
        return AgentDetailView(
            detail.title,
            detail.body,
            detail.checks,
            tuple(actions),
        )

    def _refresh_key_binding_help(self) -> None:
        node_id = getattr(self, "_selected_node_id", "")
        if node_id:
            self._select_node(node_id)

    def _render_detail(self, detail: AgentDetailView) -> None:
        node_id = getattr(self, "_selected_node_id", "")
        node = self._node_by_id(node_id) if node_id else None
        self._detail_title.setText(detail.title)
        self._detail_body.setText(detail.body)

        if node is None:
            self._set_status("не определена", warning=True)
            self._detail_type_value.setText("Неизвестная точка")
            self._detail_parent_value.setText("—")
            self._detail_branch_value.setText("—")
            self._detail_dependency.setText(
                "Точка отсутствует в текущем lineage; действия заблокированы."
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
                node.is_current or self._state.current_node_id() == node.node_id
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
                self._node_type_label(node.node_id, is_custom=is_custom)
            )
            self._detail_parent_value.setText(self._parent_title(node.parent_id))
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

        self._fill_information_rows(self._checks_layout, detail.checks, "✓")
        self._fill_information_rows(self._actions_layout, detail.actions, "→")
        content = getattr(self, "_details_content", None)
        if content is not None:
            self._constrain_text_widgets(content)

    def _fill_information_rows(
        self,
        layout: QGridLayout,
        values: tuple[str, ...],
        prefix: str,
    ) -> None:
        self._clear_layout(layout)
        for index, value in enumerate(values or ("Нет данных",)):
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(8)
            marker = QLabel(prefix)
            marker.setObjectName("CardTitle")
            text = make_muted_label(value)
            row_layout.addWidget(marker, 0, Qt.AlignmentFlag.AlignTop)
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
            return "Корневая точка"
        parent = self._node_by_id(parent_id)
        if parent is None:
            return parent_id
        return self._display_node_title(parent.title)

    @staticmethod
    def _display_node_title(title: str) -> str:
        for prefix in (
            "Base · ",
            "Dataset · ",
            "Train · ",
            "Version · ",
            "Portrait · ",
            "Delta · ",
        ):
            if title.startswith(prefix):
                return title.removeprefix(prefix)
        return title

    @staticmethod
    def _node_type_label(node_id: str, *, is_custom: bool) -> str:
        if is_custom:
            return "Локальная версия / экспериментальная ветка"
        return {
            "base": "Базовая модель",
            "dataset": "Набор данных",
            "training": "Запуск обучения",
            "snapshot": "Снимок весов / версия модели",
            "portrait": "Психологический портрет",
            "delta": "Сравнение портретов",
        }.get(node_id, "Точка lineage")

    @staticmethod
    def _version_status_text(
        status: str,
        *,
        is_current: bool,
        is_archived: bool,
    ) -> str:
        if is_current:
            return "актуальная"
        if is_archived:
            return "архивная"
        return status or "без статуса"

    @staticmethod
    def _branch_label(
        branch_note: str,
        *,
        is_current: bool,
        is_archived: bool,
    ) -> str:
        if is_current:
            return "Текущая рабочая линия"
        if is_archived:
            return "Архивная боковая ветка"
        if branch_note == "side":
            return "Боковая экспериментальная ветка"
        return "Основная линия"

    @staticmethod
    def _dependency_text(
        node_id: str,
        *,
        is_custom: bool,
        is_current: bool,
        is_archived: bool,
    ) -> str:
        if is_current:
            return (
                "Эта точка сейчас активна. Удаление заблокировано; перед заменой "
                "нужно выбрать другую актуальную версию."
            )
        if is_archived:
            return (
                "Архивная ветка не участвует в новых продолжениях. Её всё ещё "
                "можно сравнивать, но сначала нужно вернуть из архива для работы."
            )
        if is_custom:
            return (
                "Локальная ветка пока существует только в lineage. Перед обучением "
                "ей понадобятся snapshot, протокол и привязка к training run."
            )
        return {
            "base": "Исходная модель является корнем lineage и не удаляется.",
            "dataset": (
                "Изменение датасета влияет на все последующие training run и версии."
            ),
            "training": (
                "Запуск обучения нельзя считать версией до появления сохранённого artifact."
            ),
            "snapshot": (
                "Снимок связан с training run и artifact; он пригоден для портрета "
                "и сравнения только пока эти зависимости доступны."
            ),
            "portrait": (
                "Портрет корректно сравнивать только при одинаковой батарее и scoring rules."
            ),
            "delta": (
                "Delta зависит от двух портретов и не должна переживать удаление любого из них."
            ),
        }.get(node_id, "Проверьте связанные записи перед изменением этой точки.")

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
            "make_current": is_version and not is_current and not is_archived,
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
        self._make_current_action.setEnabled(capabilities["make_current"])
        self._compare_action.setEnabled(capabilities["compare"])
        self._portrait_action.setEnabled(capabilities["portrait"])
        self._branch_action.setEnabled(capabilities["branch"])
        self._delete_action.setEnabled(capabilities["delete"])

        self._make_current_action.setToolTip(
            "Уже является актуальной версией."
            if is_current
            else (
                "Архивную ветку сначала нужно вернуть из архива."
                if is_archived
                else "Сделать выбранную версию рабочей точкой lineage."
            )
        )
        self._compare_action.setToolTip(
            "Текущую версию нельзя сравнить саму с собой."
            if is_current
            else "Открыть анализ для сравнения с актуальной версией."
        )
        self._portrait_action.setToolTip(
            "Открыть батареи тестирования для выбранной версии."
        )
        self._branch_action.setToolTip(
            "Архивная ветка не продолжается."
            if is_archived
            else "Создать локальное продолжение от выбранной точки."
        )
        self._delete_action.setToolTip(
            "Удаляются только локальные неактуальные ветки."
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

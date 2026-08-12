from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import (
    make_muted_label,
    make_status_label,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.viewmodels.dashboard import (
    DashboardRoute,
    DashboardText,
    DashboardViewModel,
)


class _NavigationCard(QFrame):
    clicked = Signal()

    def __init__(self, object_name: str) -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setProperty("interactive", True)
        self._pressed = False

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            activate = self._pressed and self.rect().contains(
                event.position().toPoint()
            )
            self._pressed = False
            if activate:
                self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in {
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        }:
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class DashboardScreen(QWidget):
    navigate_requested = Signal(str, str)

    def __init__(
        self,
        view_model: DashboardViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        main_column = QVBoxLayout()
        main_column.setSpacing(16)
        side_column = QVBoxLayout()
        side_column.setSpacing(16)
        root.addLayout(main_column, 4)
        root.addLayout(side_column, 2)

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(8)
        title = self._bound_label(
            "dashboard.title",
            object_name="ScreenTitle",
        )
        subtitle = self._bound_label("dashboard.subtitle", muted=True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_column.addWidget(header)

        self._stats_grid = QGridLayout()
        self._stats_grid.setSpacing(12)
        main_column.addLayout(self._stats_grid)

        self._actions_card = self._localized_card(
            "dashboard.actions.title",
            "dashboard.actions.description",
        )
        self._actions_grid = QGridLayout()
        self._actions_grid.setSpacing(12)
        self._actions_card._layout.addLayout(self._actions_grid)
        main_column.addWidget(self._actions_card)

        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(16)
        main_column.addLayout(bottom_grid, 1)

        self._activity_card = self._localized_card(
            "dashboard.activity.title",
            "dashboard.activity.description",
        )
        bottom_grid.addWidget(self._activity_card, 0, 0)

        self._system_card = self._localized_card(
            "dashboard.system.title",
            "dashboard.system.description",
        )
        bottom_grid.addWidget(self._system_card, 0, 1)

        self._attention_card = self._localized_card(
            "dashboard.attention.title",
            "dashboard.attention.description",
        )
        side_column.addWidget(self._attention_card)

        self._lineage_card = self._localized_card(
            "dashboard.lineage.title",
            "dashboard.lineage.description",
        )
        side_column.addWidget(self._lineage_card)
        side_column.addStretch(1)

        self._refresh_all()
        if localization is not None:
            localization.language_changed.connect(self._on_language_changed)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        self._refresh_all()
        super().showEvent(event)

    def _bound_label(
        self,
        key: str,
        *,
        object_name: str = "",
        muted: bool = False,
    ) -> QLabel:
        label = make_muted_label("") if muted else QLabel()
        if object_name:
            label.setObjectName(object_name)
        if self._localization is not None:
            self._localization.bind_text(label, key)
        else:
            label.setText(self._text(key))
        return label

    def _localized_card(
        self,
        title_key: str,
        description_key: str,
    ) -> PanelCard:
        card = PanelCard()
        title = self._bound_label(title_key, object_name="SectionTitle")
        description = self._bound_label(description_key, muted=True)
        card.add_widget(title)
        card.add_widget(description)
        return card

    def _on_language_changed(self, _locale: str = "") -> None:
        self._refresh_all()

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)
            if widget is not None:
                widget.deleteLater()

    def _clear_card_body(self, card: PanelCard) -> None:
        while card._layout.count() > 2:
            item = card._layout.takeAt(2)
            if item is None:
                continue
            widget = item.widget()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)
            if widget is not None:
                widget.deleteLater()

    def _refresh_all(self) -> None:
        self._refresh_stats()
        self._refresh_actions()
        self._refresh_activity()
        self._refresh_system()
        self._refresh_attention()
        self._refresh_lineage()

    def _refresh_stats(self) -> None:
        self._clear_layout(self._stats_grid)
        for index, item in enumerate(self._vm.stats()):
            card = PanelCard(
                self._text(item.label_key),
                self._render(item.note),
                accented=(index == 0),
            )
            value_label = QLabel(self._render(item.value))
            value_label.setObjectName("MetricValue")
            value_label.setWordWrap(True)
            card.add_widget(value_label)
            self._stats_grid.addWidget(card, index // 2, index % 2)

    def _refresh_actions(self) -> None:
        self._clear_layout(self._actions_grid)
        for index, item in enumerate(self._vm.quick_actions()):
            action = _NavigationCard("ActionCard")
            workspace_title = self._text(f"nav.{item.route.screen}")
            action.setToolTip(
                self._text(
                    "dashboard.tooltip.open_workspace",
                    title=workspace_title,
                )
            )
            action.clicked.connect(
                lambda route=item.route: self._emit_route(route)
            )
            action_layout = QVBoxLayout(action)
            action_layout.setContentsMargins(16, 16, 16, 16)
            action_layout.setSpacing(10)

            top = QHBoxLayout()
            icon = QLabel(item.icon)
            icon.setObjectName("ActionIcon")
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedSize(34, 34)
            icon.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            top.addWidget(icon, 0, Qt.AlignmentFlag.AlignLeft)
            top.addStretch(1)
            action_layout.addLayout(top)

            title_label = QLabel(self._render(item.title))
            title_label.setObjectName("CardTitle")
            title_label.setWordWrap(True)
            title_label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            description = make_muted_label(self._render(item.description))
            description.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            action_layout.addWidget(title_label)
            action_layout.addWidget(description)
            self._actions_grid.addWidget(action, index // 3, index % 3)

    def _refresh_activity(self) -> None:
        self._clear_card_body(self._activity_card)
        for item in self._vm.recent_activity():
            row = _NavigationCard("PanelCardSoft")
            row.setToolTip(self._text("dashboard.tooltip.open_related"))
            row.clicked.connect(
                lambda route=item.route: self._emit_route(route)
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 12, 14, 12)
            row_layout.setSpacing(12)
            texts = QVBoxLayout()

            if item.empty_title is not None:
                title_text = self._render(item.empty_title)
            else:
                title_text = self._text(
                    "dashboard.activity.item.title",
                    kind=self._text(item.kind_key),
                    title=self._render_value(item.title),
                )
            title = QLabel(title_text)
            title.setWordWrap(True)
            title.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            note = make_muted_label(self._render(item.detail))
            note.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            texts.addWidget(title)
            texts.addWidget(note)
            row_layout.addLayout(texts, 1)

            tone = (
                "pending"
                if item.state_key
                in {
                    "dashboard.state.attention",
                    "dashboard.state.waiting",
                }
                else "good"
            )
            state = make_status_label(
                self._text(item.state_key),
                tone=tone,
            )
            state.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            row_layout.addWidget(state, 0, Qt.AlignmentFlag.AlignTop)
            self._activity_card.add_widget(row)

    def _refresh_system(self) -> None:
        self._clear_card_body(self._system_card)
        for item in self._vm.system_metrics():
            line = QWidget()
            line.setProperty("transparentBg", True)
            line_layout = QVBoxLayout(line)
            line_layout.setContentsMargins(0, 0, 0, 0)
            line_layout.setSpacing(6)
            top = QHBoxLayout()
            top.addWidget(QLabel(self._text(item.label_key)))
            note_label = QLabel(self._render(item.note))
            note_label.setObjectName("MutedText")
            note_label.setWordWrap(True)
            top.addStretch(1)
            top.addWidget(note_label)
            bar = QProgressBar()
            bar.setObjectName("MetricProgress")
            bar.setRange(0, 100)
            bar.setValue(item.value)
            bar.setTextVisible(False)
            line_layout.addLayout(top)
            line_layout.addWidget(bar)
            self._system_card.add_widget(line)

        step = self._vm.next_best_step()
        warning = _NavigationCard("WarningBlock")
        warning.setToolTip(self._text("dashboard.tooltip.next_step"))
        warning.clicked.connect(
            lambda route=step.route: self._emit_route(route)
        )
        warning_layout = QVBoxLayout(warning)
        warning_layout.setContentsMargins(14, 12, 14, 12)
        warning_layout.setSpacing(8)
        warning_title = QLabel(self._text("dashboard.next_step.title"))
        warning_title.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        warning_text = make_muted_label(self._render(step.message))
        warning_text.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        warning_layout.addWidget(warning_title)
        warning_layout.addWidget(warning_text)
        self._system_card.add_widget(warning)

    def _refresh_attention(self) -> None:
        self._clear_card_body(self._attention_card)
        for item in self._vm.attention_items():
            block = QFrame()
            block.setObjectName("PanelCardSoft")
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(14, 12, 14, 12)
            block_layout.setSpacing(8)
            title = QLabel(self._text(item.title_key))
            title.setWordWrap(True)
            block_layout.addWidget(title)
            block_layout.addWidget(
                make_muted_label(self._render(item.body))
            )
            self._attention_card.add_widget(block)

    def _refresh_lineage(self) -> None:
        self._clear_card_body(self._lineage_card)
        for item in self._vm.quick_lineage():
            pill = _NavigationCard("LineageRow")
            pill.setToolTip(self._text("dashboard.tooltip.open_stage"))
            pill.clicked.connect(
                lambda route=item.route: self._emit_route(route)
            )
            pill_layout = QHBoxLayout(pill)
            pill_layout.setContentsMargins(12, 10, 12, 10)
            pill_layout.setSpacing(10)
            chevron = QLabel("›")
            chevron.setObjectName("LineageIcon")
            chevron.setFixedSize(22, 22)
            chevron.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chevron.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            pill_layout.addWidget(chevron)
            label = QLabel(
                self._text(
                    "dashboard.lineage.item",
                    label=self._text(item.label_key),
                    value=self._render_value(item.value),
                )
            )
            label.setWordWrap(True)
            label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            pill_layout.addWidget(label, 1)
            self._lineage_card.add_widget(pill)

    def _emit_route(self, route: DashboardRoute) -> None:
        focus = self._text(route.focus_key) if route.focus_key else ""
        self.navigate_requested.emit(route.screen, focus)

    def _render_value(self, value: str | DashboardText) -> str:
        return self._render(value) if isinstance(value, DashboardText) else value

    def _render(self, message: DashboardText) -> str:
        values = {
            key: self._render(value) if isinstance(value, DashboardText) else value
            for key, value in message.values.items()
        }
        return self._text(message.key, **values)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

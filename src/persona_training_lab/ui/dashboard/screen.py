from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
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
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel


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

    def __init__(self, view_model: DashboardViewModel) -> None:
        super().__init__()
        self._vm = view_model

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
        title = QLabel("Панель управления")
        title.setObjectName("ScreenTitle")
        subtitle = make_muted_label(
            "Живая сводка: обучение, датасеты, снимки, портрет и delta модели"
        )
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_column.addWidget(header)

        self._stats_grid = QGridLayout()
        self._stats_grid.setSpacing(12)
        main_column.addLayout(self._stats_grid)

        self._actions_card = PanelCard(
            "Быстрые действия",
            "Короткий маршрут к следующему рабочему шагу. Карточки можно нажимать.",
        )
        self._actions_grid = QGridLayout()
        self._actions_grid.setSpacing(12)
        self._actions_card._layout.addLayout(self._actions_grid)
        main_column.addWidget(self._actions_card)

        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(16)
        main_column.addLayout(bottom_grid, 1)

        self._activity_card = PanelCard(
            "Последняя активность",
            "Где система остановилась и что уже есть в базе.",
        )
        bottom_grid.addWidget(self._activity_card, 0, 0)

        self._system_card = PanelCard(
            "Готовность пайплайна",
            "Проверка ключевых условий перед следующим шагом.",
        )
        bottom_grid.addWidget(self._system_card, 0, 1)

        self._attention_card = PanelCard(
            "Панель внимания",
            "То, что лучше не потерять из виду.",
        )
        side_column.addWidget(self._attention_card)

        self._lineage_card = PanelCard(
            "Lineage-цепочка",
            "Нажмите этап, чтобы сразу перейти к его рабочей вкладке.",
        )
        side_column.addWidget(self._lineage_card)
        side_column.addStretch(1)

        self._refresh_all()

    def showEvent(self, event) -> None:  # type: ignore[override]
        self._refresh_all()
        super().showEvent(event)

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)
            if widget is not None:
                widget.deleteLater()

    def _clear_card_body(self, card: PanelCard) -> None:
        while card._layout.count() > 2:
            item = card._layout.takeAt(2)
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
        for index, (label, value, note) in enumerate(self._vm.stats()):
            card = PanelCard(label, note, accented=(index == 0))
            value_label = QLabel(value)
            value_label.setObjectName("MetricValue")
            value_label.setWordWrap(True)
            card.add_widget(value_label)
            self._stats_grid.addWidget(card, index // 2, index % 2)

    def _refresh_actions(self) -> None:
        self._clear_layout(self._actions_grid)
        for index, (icon_text, title_text, desc_text) in enumerate(
            self._vm.quick_actions()
        ):
            action = _NavigationCard("ActionCard")
            target, focus = self._quick_action_target(index, desc_text)
            action.setToolTip(f"Открыть вкладку «{target}»")
            action.clicked.connect(
                lambda target=target, focus=focus: self.navigate_requested.emit(
                    target,
                    focus,
                )
            )
            action_layout = QVBoxLayout(action)
            action_layout.setContentsMargins(16, 16, 16, 16)
            action_layout.setSpacing(10)

            top = QHBoxLayout()
            icon = QLabel(icon_text)
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

            title_label = QLabel(title_text)
            title_label.setObjectName("CardTitle")
            title_label.setWordWrap(True)
            title_label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            description = make_muted_label(desc_text)
            description.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            action_layout.addWidget(title_label)
            action_layout.addWidget(description)
            self._actions_grid.addWidget(action, index // 3, index % 3)

    def _refresh_activity(self) -> None:
        self._clear_card_body(self._activity_card)
        for title_text, note_text in self._vm.recent_activity():
            target, focus = self._activity_target(title_text)
            row = _NavigationCard("PanelCardSoft")
            row.setToolTip("Открыть связанную рабочую вкладку")
            row.clicked.connect(
                lambda target=target, focus=focus: self.navigate_requested.emit(
                    target,
                    focus,
                )
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 12, 14, 12)
            row_layout.setSpacing(12)
            texts = QVBoxLayout()
            title = QLabel(title_text)
            title.setWordWrap(True)
            title.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            note = make_muted_label(note_text)
            note.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            texts.addWidget(title)
            texts.addWidget(note)
            row_layout.addLayout(texts, 1)
            state = self._state_label(note_text)
            state.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            row_layout.addWidget(state, 0, Qt.AlignmentFlag.AlignTop)
            self._activity_card.add_widget(row)

    def _refresh_system(self) -> None:
        self._clear_card_body(self._system_card)
        for label_text, value, note in self._vm.system_metrics():
            line = QWidget()
            line.setProperty("transparentBg", True)
            line_layout = QVBoxLayout(line)
            line_layout.setContentsMargins(0, 0, 0, 0)
            line_layout.setSpacing(6)
            top = QHBoxLayout()
            top.addWidget(QLabel(label_text))
            note_label = QLabel(note)
            note_label.setObjectName("MutedText")
            note_label.setWordWrap(True)
            top.addStretch(1)
            top.addWidget(note_label)
            bar = QProgressBar()
            bar.setObjectName("MetricProgress")
            bar.setRange(0, 100)
            bar.setValue(value)
            bar.setTextVisible(False)
            line_layout.addLayout(top)
            line_layout.addWidget(bar)
            self._system_card.add_widget(line)

        step = self._vm.next_best_step()
        target, focus = self._target_for_step(step)
        warning = _NavigationCard("WarningBlock")
        warning.setToolTip("Перейти к следующему этапу")
        warning.clicked.connect(
            lambda: self.navigate_requested.emit(target, focus)
        )
        warning_layout = QVBoxLayout(warning)
        warning_layout.setContentsMargins(14, 12, 14, 12)
        warning_layout.setSpacing(8)
        warning_title = QLabel(
            "Следующий шаг · нажмите, чтобы продолжить"
        )
        warning_title.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        warning_text = make_muted_label(step)
        warning_text.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        warning_layout.addWidget(warning_title)
        warning_layout.addWidget(warning_text)
        self._system_card.add_widget(warning)

    def _refresh_attention(self) -> None:
        self._clear_card_body(self._attention_card)
        for title_text, body in self._vm.attention_items():
            block = QFrame()
            block.setObjectName("PanelCardSoft")
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(14, 12, 14, 12)
            block_layout.setSpacing(8)
            title = QLabel(title_text)
            title.setWordWrap(True)
            block_layout.addWidget(title)
            block_layout.addWidget(make_muted_label(body))
            self._attention_card.add_widget(block)

    def _refresh_lineage(self) -> None:
        self._clear_card_body(self._lineage_card)
        for item in self._vm.quick_lineage():
            target, focus = self._lineage_target(item)
            pill = _NavigationCard("LineageRow")
            pill.setToolTip("Открыть этот этап")
            pill.clicked.connect(
                lambda target=target, focus=focus: self.navigate_requested.emit(
                    target,
                    focus,
                )
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
            label = QLabel(item)
            label.setWordWrap(True)
            label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )
            pill_layout.addWidget(label, 1)
            self._lineage_card.add_widget(pill)

    def _quick_action_target(
        self,
        index: int,
        description: str,
    ) -> tuple[str, str]:
        if index == 0:
            return self._target_for_step(description)
        if index == 1:
            return "tests", "Собрать портрет"
        return "analysis", ""

    @staticmethod
    def _target_for_step(step: str) -> tuple[str, str]:
        lowered = step.casefold()
        if "датасет" in lowered:
            return "datasets", "Добав"
        if "сним" in lowered or "верс" in lowered:
            return "snapshots", ""
        if "training" in lowered or "обучен" in lowered or "artifact" in lowered:
            return "training", "Запуст"
        if "портрет" in lowered or "score" in lowered:
            return "tests", "Собрать портрет"
        if "анализ" in lowered or "delta" in lowered:
            return "analysis", ""
        if "документ" in lowered:
            return "docs", ""
        return "dashboard", ""

    @staticmethod
    def _activity_target(title: str) -> tuple[str, str]:
        lowered = title.casefold()
        if "training" in lowered:
            return "training", ""
        if "snapshot" in lowered:
            return "snapshots", ""
        if "portrait" in lowered:
            return "tests", ""
        if "dataset" in lowered:
            return "datasets", ""
        return "dashboard", ""

    @staticmethod
    def _lineage_target(item: str) -> tuple[str, str]:
        lowered = item.casefold()
        if lowered.startswith("base"):
            return "agents", ""
        if lowered.startswith("dataset"):
            return "datasets", ""
        if lowered.startswith("training"):
            return "training", ""
        if lowered.startswith("snapshot"):
            return "snapshots", ""
        if lowered.startswith("portrait"):
            return "tests", ""
        return "agents", ""

    def _state_label(self, note_text: str) -> QLabel:
        text = "есть"
        warning = False
        lowered = note_text.lower()
        if (
            "ошиб" in lowered
            or "invalid" in lowered
            or "внимание" in lowered
        ):
            text = "внимание"
            warning = True
        elif "нет" in lowered or "—" in note_text:
            text = "ожидание"
            warning = True
        elif (
            "готов" in lowered
            or "собран" in lowered
            or "заверш" in lowered
            or "valid" in lowered
        ):
            text = "готово"
        return make_status_label(text, warning=warning)

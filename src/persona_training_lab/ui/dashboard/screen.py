from __future__ import annotations

from PySide6.QtCore import Qt
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
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel


class DashboardScreen(QWidget):
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
        subtitle = make_muted_label("Живая сводка: обучение, датасеты, снимки, портрет и delta модели")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_column.addWidget(header)

        self._stats_grid = QGridLayout()
        self._stats_grid.setSpacing(12)
        main_column.addLayout(self._stats_grid)

        self._actions_card = PanelCard("Быстрые действия", "Короткий маршрут к следующему рабочему шагу.")
        self._actions_grid = QGridLayout()
        self._actions_grid.setSpacing(12)
        self._actions_card._layout.addLayout(self._actions_grid)
        main_column.addWidget(self._actions_card)

        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(16)
        main_column.addLayout(bottom_grid, 1)

        self._activity_card = PanelCard("Последняя активность", "Где система остановилась и что уже есть в базе.")
        bottom_grid.addWidget(self._activity_card, 0, 0)

        self._system_card = PanelCard("Готовность пайплайна", "Проверка ключевых условий перед следующим шагом.")
        bottom_grid.addWidget(self._system_card, 0, 1)

        self._attention_card = PanelCard("Панель внимания", "То, что лучше не потерять из виду.")
        side_column.addWidget(self._attention_card)

        self._lineage_card = PanelCard("Lineage-цепочка", "Связка данных, обучения, snapshot и портрета.")
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
        # Preserve the title and subtitle labels that PanelCard created first.
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
        for index, (icon_text, title_text, desc_text) in enumerate(self._vm.quick_actions()):
            action = QFrame()
            action.setObjectName("ActionCard")
            action_layout = QVBoxLayout(action)
            action_layout.setContentsMargins(16, 16, 16, 16)
            action_layout.setSpacing(10)

            top = QHBoxLayout()
            icon = QLabel(icon_text)
            icon.setObjectName("ActionIcon")
            icon.setAlignment(Qt.AlignCenter)
            icon.setFixedSize(34, 34)
            top.addWidget(icon, 0, Qt.AlignLeft)
            top.addStretch(1)
            action_layout.addLayout(top)

            title_label = QLabel(title_text)
            title_label.setObjectName("CardTitle")
            title_label.setWordWrap(True)
            action_layout.addWidget(title_label)
            action_layout.addWidget(make_muted_label(desc_text))
            self._actions_grid.addWidget(action, index // 3, index % 3)

    def _refresh_activity(self) -> None:
        self._clear_card_body(self._activity_card)
        for title_text, note_text in self._vm.recent_activity():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 12, 14, 12)
            row_layout.setSpacing(12)
            texts = QVBoxLayout()
            title = QLabel(title_text)
            title.setWordWrap(True)
            texts.addWidget(title)
            texts.addWidget(make_muted_label(note_text))
            row_layout.addLayout(texts, 1)
            row_layout.addWidget(self._state_label(note_text), 0, Qt.AlignTop)
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

        warning = QFrame()
        warning.setObjectName("WarningBlock")
        warning_layout = QVBoxLayout(warning)
        warning_layout.setContentsMargins(14, 12, 14, 12)
        warning_layout.setSpacing(8)
        warning_layout.addWidget(QLabel("Следующий шаг"))
        warning_layout.addWidget(make_muted_label(self._vm.next_best_step()))
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
            pill = QFrame()
            pill.setObjectName("LineageRow")
            pill_layout = QHBoxLayout(pill)
            pill_layout.setContentsMargins(12, 10, 12, 10)
            pill_layout.setSpacing(10)
            chevron = QLabel("›")
            chevron.setObjectName("LineageIcon")
            chevron.setFixedSize(22, 22)
            chevron.setAlignment(Qt.AlignCenter)
            pill_layout.addWidget(chevron)
            label = QLabel(item)
            label.setWordWrap(True)
            pill_layout.addWidget(label, 1)
            self._lineage_card.add_widget(pill)

    def _state_label(self, note_text: str) -> QLabel:
        text = "есть"
        warning = False
        lowered = note_text.lower()
        if "ошиб" in lowered or "invalid" in lowered or "внимание" in lowered:
            text = "внимание"
            warning = True
        elif "нет" in lowered or "—" in note_text:
            text = "ожидание"
            warning = True
        elif "готов" in lowered or "собран" in lowered or "заверш" in lowered or "valid" in lowered:
            text = "готово"
        return make_status_label(text, warning=warning)

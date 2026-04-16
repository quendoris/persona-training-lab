from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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
        subtitle = make_muted_label("Спокойная обзорная панель, где видно весь жизненный цикл личности модели")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_column.addWidget(header)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)
        for index, (label, value, note) in enumerate(self._vm.stats()):
            card = PanelCard(label, note, accented=(index == 0))
            value_label = QLabel(value)
            value_label.setObjectName("MetricValue")
            card.add_widget(value_label)
            stats_grid.addWidget(card, index // 2, index % 2)
        main_column.addLayout(stats_grid)

        actions_card = PanelCard(
            "Быстрые действия",
            "Сильные точки входа в живой workflow системы.",
        )
        actions_grid = QGridLayout()
        actions_grid.setSpacing(12)
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
            action_layout.addWidget(title_label)
            action_layout.addWidget(make_muted_label(desc_text))
            actions_grid.addWidget(action, index // 3, index % 3)
        actions_card._layout.addLayout(actions_grid)
        main_column.addWidget(actions_card)

        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(16)

        activity_card = PanelCard(
            "Последняя активность",
            "Система должна помнить, где ты остановился, и помогать вернуться в поток.",
        )
        for title_text, note_text in self._vm.recent_activity():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 12, 14, 12)
            row_layout.setSpacing(12)
            texts = QVBoxLayout()
            texts.addWidget(QLabel(title_text))
            texts.addWidget(make_muted_label(note_text))
            row_layout.addLayout(texts, 1)
            state = make_status_label("идёт")
            if "проверенный" in note_text:
                state.setText("проверен")
            elif "одобрена" in note_text:
                state.setText("одобрен")
            elif "предупреждениями" in note_text:
                state.setText("внимание")
                state.setObjectName("StatusWarning")
            row_layout.addWidget(state, 0, Qt.AlignTop)
            activity_card.add_widget(row)
        bottom_grid.addWidget(activity_card, 0, 0)

        system_card = PanelCard(
            "Состояние системы",
            "Мониторинг как часть доверия к среде.",
        )
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
            top.addStretch(1)
            top.addWidget(note_label)
            bar = QProgressBar()
            bar.setObjectName("MetricProgress")
            bar.setRange(0, 100)
            bar.setValue(value)
            bar.setTextVisible(False)
            line_layout.addLayout(top)
            line_layout.addWidget(bar)
            system_card.add_widget(line)
        warning = QFrame()
        warning.setObjectName("WarningBlock")
        warning_layout = QVBoxLayout(warning)
        warning_layout.setContentsMargins(14, 12, 14, 12)
        warning_layout.setSpacing(8)
        warning_layout.addWidget(QLabel("Мягкое предупреждение"))
        warning_layout.addWidget(make_muted_label("У версии датасета dsv_curated_rose_07 осталось одно семантическое предупреждение, но обучение можно продолжать."))
        system_card.add_widget(warning)
        bottom_grid.addWidget(system_card, 0, 1)

        main_column.addLayout(bottom_grid, 1)

        attention_card = PanelCard("Панель внимания", "То, что лучше не потерять из виду.")
        for title_text, body in self._vm.attention_items():
            block = QFrame()
            block.setObjectName("PanelCardSoft")
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(14, 12, 14, 12)
            block_layout.setSpacing(8)
            block_layout.addWidget(QLabel(title_text))
            block_layout.addWidget(make_muted_label(body))
            attention_card.add_widget(block)
        side_column.addWidget(attention_card)

        lineage_card = PanelCard("Быстрая lineage-цепочка", "Связи должны ощущаться живыми, а не спрятанными.")
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
            pill_layout.addWidget(QLabel(item), 1)
            lineage_card.add_widget(pill)
        side_column.addWidget(lineage_card)
        side_column.addStretch(1)

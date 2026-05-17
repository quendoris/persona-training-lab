from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.viewmodels.agents import AgentsViewModel


class AgentsScreen(QWidget):
    def __init__(self, view_model: AgentsViewModel) -> None:
        super().__init__()
        self._vm = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        title, subtitle = self._vm.header_summary()

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(8)
        header_title = QLabel(f"Агенты · {title}")
        header_title.setObjectName("ScreenTitle")
        header_layout.addWidget(header_title)
        header_layout.addWidget(make_muted_label(subtitle))
        root.addWidget(header)

        registry = PanelCard("Реестр агентов", "Слой активных сущностей для запусков и экспериментов.")
        for _agent_id, item_title, item_subtitle, item_status in self._vm.agents():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(10)
            row_text = QVBoxLayout()
            row_text.setSpacing(4)
            row_text.addWidget(QLabel(item_title))
            row_text.addWidget(make_muted_label(item_subtitle))
            row_layout.addLayout(row_text, 1)
            row_layout.addWidget(make_muted_label(item_status))
            registry.add_widget(row)

        root.addWidget(registry)
        root.addStretch(1)

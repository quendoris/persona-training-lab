from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
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
        header_title = QLabel(title)
        header_title.setObjectName("ScreenTitle")
        header_layout.addWidget(header_title)
        header_layout.addWidget(make_muted_label(subtitle))
        root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        roles_card = PanelCard("Рабочие роли", "Роли не действуют автономно: они подсказывают следующий шаг.")
        for role in self._vm.roles():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(6)
            top = QHBoxLayout()
            title_label = QLabel(role.title)
            title_label.setObjectName("CardTitle")
            top.addWidget(title_label, 1)
            top.addWidget(make_status_label(role.status, warning=role.status in {"позже", "проверка"}))
            row_layout.addLayout(top)
            row_layout.addWidget(make_muted_label(role.mission))
            next_label = QLabel(f"→ {role.next_action}")
            next_label.setWordWrap(True)
            row_layout.addWidget(next_label)
            roles_card.add_widget(row)
        body.addWidget(roles_card, 2)

        lineage_card = PanelCard("Дерево версии", "Модель как цепочка: dataset → training → snapshot → portrait → delta.")
        for node in self._vm.version_nodes():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(10)
            indent = QLabel("" if node.depth == 0 else "  " * node.depth + "↳")
            indent.setObjectName("LineageIcon")
            indent.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            row_layout.addWidget(indent)
            text_col = QVBoxLayout()
            text_col.setSpacing(4)
            title_label = QLabel(node.title)
            title_label.setWordWrap(True)
            text_col.addWidget(title_label)
            text_col.addWidget(make_muted_label(node.subtitle))
            row_layout.addLayout(text_col, 1)
            row_layout.addWidget(make_status_label(node.status, warning=node.status in {"ожидание", "ошибка"}), 0, Qt.AlignTop)
            lineage_card.add_widget(row)
        body.addWidget(lineage_card, 3)

        detail_card = PanelCard("Карточка версии", "Что известно о текущей версии и что проверить перед откатом/сравнением.")
        detail = self._vm.selected_detail()
        detail_title = QLabel(detail.title)
        detail_title.setObjectName("CardTitle")
        detail_card.add_widget(detail_title)
        detail_body = QLabel(detail.body)
        detail_body.setWordWrap(True)
        detail_card.add_widget(detail_body)

        checks_grid = QGridLayout()
        checks_grid.setSpacing(8)
        for index, check in enumerate(detail.checks):
            check_row = QFrame()
            check_row.setObjectName("PanelCardSoft")
            check_layout = QHBoxLayout(check_row)
            check_layout.setContentsMargins(10, 8, 10, 8)
            check_layout.addWidget(QLabel("✓"))
            check_label = make_muted_label(check)
            check_layout.addWidget(check_label, 1)
            checks_grid.addWidget(check_row, index, 0)
        detail_card._layout.addLayout(checks_grid)
        body.addWidget(detail_card, 2)

        root.addStretch(0)

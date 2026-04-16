from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class IssuesPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title = QLabel("Проблемы")
        subtitle = QLabel("Сюда попадают важные предупреждения и вопросы, которые лучше не терять.")
        subtitle.setObjectName("MutedText")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        for line in [
            "• 1 семантическое предупреждение по датасету",
            "• 0 критических проблем целостности",
            "• 1 результат сравнения готов",
        ]:
            layout.addWidget(QLabel(line))
        layout.addStretch(1)

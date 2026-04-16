from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class InspectorPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title = QLabel("Инспектор")
        subtitle = QLabel("Здесь появятся детали выбранного объекта.")
        subtitle.setObjectName("MutedText")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)

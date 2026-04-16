from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QTextEdit


class ActivityPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title = QLabel("Активность")
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "[evt] App started\n"
            "[evt] Workspace ready\n"
            "[evt] UI shell initialized\n"
        )
        layout.addWidget(title)
        layout.addWidget(text)

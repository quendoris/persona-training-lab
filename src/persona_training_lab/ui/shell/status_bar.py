from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar


class AppStatusBar(QStatusBar):
    def __init__(self) -> None:
        super().__init__()
        self._left = QLabel("Готово")
        self._right = QLabel("Velvet · Cyan")
        self.addWidget(self._left)
        self.addPermanentWidget(self._right)

    def set_message(self, text: str) -> None:
        self._left.setText(text)

    def set_style_message(self, text: str) -> None:
        self._right.setText(text)

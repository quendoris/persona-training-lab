from __future__ import annotations

from PySide6.QtWidgets import QLabel


class StatusBadge(QLabel):
    def __init__(self, text: str, warning: bool = False) -> None:
        super().__init__(text)
        self.setObjectName("StatusWarning" if warning else "StatusSuccess")

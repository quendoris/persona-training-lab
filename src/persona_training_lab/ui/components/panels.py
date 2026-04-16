from __future__ import annotations

from PySide6.QtWidgets import QLabel


def make_muted_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("MutedText")
    label.setWordWrap(True)
    return label


def make_status_label(text: str, warning: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName("StatusWarning" if warning else "StatusSuccess")
    return label

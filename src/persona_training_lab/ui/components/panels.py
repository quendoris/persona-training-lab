from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import QLabel


StatusLabelTone = Literal["good", "pending"]


def make_muted_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("MutedText")
    label.setWordWrap(True)
    return label


def make_status_label(
    text: str,
    tone: StatusLabelTone | bool = False,
) -> QLabel:
    warning = tone if isinstance(tone, bool) else tone == "pending"
    label = QLabel(text)
    label.setObjectName("StatusWarning" if warning else "StatusSuccess")
    return label

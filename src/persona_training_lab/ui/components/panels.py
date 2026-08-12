from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import QLabel


StatusLabelTone = Literal["good", "pending"]
_STATUS_OBJECT_NAMES: dict[StatusLabelTone, str] = {
    "good": "StatusSuccess",
    "pending": "StatusWarning",
}


def make_muted_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("MutedText")
    label.setWordWrap(True)
    return label


def make_status_label(
    text: str,
    tone: StatusLabelTone = "good",
) -> QLabel:
    label = QLabel(text)
    label.setObjectName(_STATUS_OBJECT_NAMES[tone])
    return label

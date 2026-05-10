from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from persona_training_lab.ui.components.panels import make_muted_label


class RoundedMetricBar(QFrame):
    def __init__(self, value: int, height: int = 12) -> None:
        super().__init__()
        self.setProperty("transparentBg", True)
        self._value = max(0, min(100, value))
        self._height = height

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._track = QFrame()
        self._track.setObjectName("TelemetryBarTrack")
        self._track.setFixedHeight(height)
        self._track.setAttribute(Qt.WA_StyledBackground, True)
        layout.addWidget(self._track)

        self._fill = QFrame(self._track)
        self._fill.setObjectName("TelemetryBarFill")
        self._fill.setAttribute(Qt.WA_StyledBackground, True)
        self._fill.show()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        width = max(self._height, int(self._track.width() * self._value / 100))
        self._fill.setGeometry(0, 0, width, self._track.height())

    def set_value(self, value: int) -> None:
        self._value = max(0, min(100, value))
        self.update()


class TraitMetricCard(QFrame):
    def __init__(self, title: str, value: int, note: str) -> None:
        super().__init__()
        self.setObjectName("PanelCardSoft")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        layout.addWidget(title_label)

        bar = RoundedMetricBar(value=value, height=12)
        layout.addWidget(bar)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.addWidget(make_muted_label(note), 1)

        value_label = QLabel(f"{value}%")
        value_label.setObjectName("MetricPercentPill")
        value_label.setAlignment(Qt.AlignCenter)
        footer.addWidget(value_label, 0, Qt.AlignRight)
        layout.addLayout(footer)

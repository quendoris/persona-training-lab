from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from persona_training_lab.ui.components.panels import make_muted_label


class PanelCard(QFrame):
    def __init__(self, title: str | None = None, subtitle: str | None = None, accented: bool = False) -> None:
        super().__init__()
        self.setObjectName("AccentCard" if accented else "PanelCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 18, 18, 18)
        self._layout.setSpacing(12)
        if title:
            title_label = QLabel(title)
            title_label.setObjectName("SectionTitle")
            self._layout.addWidget(title_label)
        if subtitle:
            self._layout.addWidget(make_muted_label(subtitle))

    def add_widget(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)

    def add_stretch(self, stretch: int = 1) -> None:
        self._layout.addStretch(stretch)

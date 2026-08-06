from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from persona_training_lab.ui.components.panels import make_muted_label


class PanelCard(QFrame):
    def __init__(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        accented: bool = False,
    ) -> None:
        super().__init__()
        self.setObjectName("AccentCard" if accented else "PanelCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 18, 18, 18)
        self._layout.setSpacing(12)
        self._title_label: QLabel | None = None
        self._subtitle_label: QLabel | None = None
        if title is not None:
            self.set_title(title)
        if subtitle is not None:
            self.set_subtitle(subtitle)

    @property
    def title_label(self) -> QLabel | None:
        return self._title_label

    @property
    def subtitle_label(self) -> QLabel | None:
        return self._subtitle_label

    def set_title(self, title: str) -> None:
        if self._title_label is None:
            self._title_label = QLabel()
            self._title_label.setObjectName("SectionTitle")
            self._layout.insertWidget(0, self._title_label)
        self._title_label.setText(title)
        self._title_label.setVisible(bool(title))

    def set_subtitle(self, subtitle: str) -> None:
        if self._subtitle_label is None:
            self._subtitle_label = make_muted_label("")
            position = 1 if self._title_label is not None else 0
            self._layout.insertWidget(position, self._subtitle_label)
        self._subtitle_label.setText(subtitle)
        self._subtitle_label.setVisible(bool(subtitle))

    def add_widget(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)

    def add_stretch(self, stretch: int = 1) -> None:
        self._layout.addStretch(stretch)

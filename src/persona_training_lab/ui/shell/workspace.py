from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QStackedWidget

from persona_training_lab.ui.themes.manager import apply_scrollbar_style


class WorkspaceStack(QScrollArea):
    """Scrollable workspace host.

    Individual screens can still own their local scroll areas, but this outer
    safety rail keeps the app usable on notebook-sized displays when a screen
    has a larger enterprise layout than the available height.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("StableScrollArea")
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._stack = QStackedWidget()
        self._stack.setProperty("transparentBg", True)
        self.setWidget(self._stack)
        apply_scrollbar_style(self)

    def register(self, key: str, widget) -> None:
        widget.setProperty("workspace_key", key)
        self._stack.addWidget(widget)

    def show_workspace(self, key: str) -> None:
        for index in range(self._stack.count()):
            widget = self._stack.widget(index)
            if widget.property("workspace_key") == key:
                self._stack.setCurrentIndex(index)
                return

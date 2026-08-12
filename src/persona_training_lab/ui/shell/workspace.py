from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QStackedWidget, QWidget

from persona_training_lab.ui.themes.manager import apply_scrollbar_style


class WorkspaceStack(QScrollArea):
    """Scrollable workspace host with an optional leave guard per screen."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("StableScrollArea")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._stack = QStackedWidget()
        self._stack.setProperty("transparentBg", True)
        self.setWidget(self._stack)
        apply_scrollbar_style(self)

    def register(self, key: str, widget: QWidget) -> None:
        widget.setProperty("workspace_key", key)
        self._stack.addWidget(widget)

    def workspace(self, key: str) -> QWidget | None:
        for index in range(self._stack.count()):
            widget = self._stack.widget(index)
            if widget is None:
                continue
            if widget.property("workspace_key") == key:
                return widget
        return None

    def current_workspace_key(self) -> str:
        current = self._stack.currentWidget()
        if current is None:
            return ""
        return str(current.property("workspace_key") or "")

    def request_current_leave(self) -> bool:
        current = self._stack.currentWidget()
        if current is None:
            return True
        guard = getattr(current, "request_leave_workspace", None)
        if not callable(guard):
            return True
        return bool(guard())

    def show_workspace(self, key: str) -> bool:
        for index in range(self._stack.count()):
            widget = self._stack.widget(index)
            if widget is None:
                continue
            if widget.property("workspace_key") != key:
                continue
            if index == self._stack.currentIndex():
                return True
            if not self.request_current_leave():
                return False
            self._stack.setCurrentIndex(index)
            return True
        return False

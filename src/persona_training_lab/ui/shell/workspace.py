from __future__ import annotations

from PySide6.QtWidgets import QStackedWidget


class WorkspaceStack(QStackedWidget):
    def register(self, key: str, widget) -> None:
        widget.setProperty("workspace_key", key)
        self.addWidget(widget)

    def show_workspace(self, key: str) -> None:
        for index in range(self.count()):
            widget = self.widget(index)
            if widget.property("workspace_key") == key:
                self.setCurrentIndex(index)
                return

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from persona_training_lab.ui.shell.workspace import WorkspaceStack


class _GuardedWidget(QWidget):
    def __init__(self, *, allow_leave: bool) -> None:
        super().__init__()
        self.allow_leave = allow_leave
        self.leave_requests = 0

    def request_leave_workspace(self) -> bool:
        self.leave_requests += 1
        return self.allow_leave


def test_workspace_keeps_current_screen_when_leave_is_rejected() -> None:
    app = QApplication.instance() or QApplication([])
    workspace = WorkspaceStack()
    guarded = _GuardedWidget(allow_leave=False)
    target = QWidget()
    workspace.register("guarded", guarded)
    workspace.register("target", target)

    assert workspace.current_workspace_key() == "guarded"
    assert workspace.show_workspace("target") is False
    assert workspace.current_workspace_key() == "guarded"
    assert guarded.leave_requests == 1

    guarded.allow_leave = True
    assert workspace.show_workspace("target") is True
    assert workspace.current_workspace_key() == "target"
    assert guarded.leave_requests == 2

    workspace.deleteLater()
    app.processEvents()

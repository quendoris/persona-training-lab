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


class _CloseAwareWidget(_GuardedWidget):
    def __init__(self, *, allow_leave: bool, allow_close: bool) -> None:
        super().__init__(allow_leave=allow_leave)
        self.allow_close = allow_close
        self.close_requests = 0

    def request_application_close(self) -> bool:
        self.close_requests += 1
        return self.allow_close


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


def test_application_close_can_use_dedicated_guard_without_relaxing_leave_guard() -> None:
    app = QApplication.instance() or QApplication([])
    workspace = WorkspaceStack()
    guarded = _CloseAwareWidget(allow_leave=False, allow_close=True)
    target = QWidget()
    workspace.register("guarded", guarded)
    workspace.register("target", target)

    assert workspace.show_workspace("target") is False
    assert guarded.leave_requests == 1
    assert workspace.request_current_close() is True
    assert guarded.close_requests == 1
    assert guarded.leave_requests == 1

    workspace.deleteLater()
    app.processEvents()

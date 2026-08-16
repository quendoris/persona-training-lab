from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow

from persona_training_lab.ui.shell.main_window_context import (
    MainWindow as _ContextMainWindow,
)


class MainWindow(_ContextMainWindow):
    """Shell that never destroys a workspace while its worker still owns data."""

    def __init__(self, *args, **kwargs) -> None:
        self._close_guard_passed = False
        self._background_close_retry_scheduled = False
        super().__init__(*args, **kwargs)

    def shutdown_background_work(self, timeout_ms: int = 6_500) -> bool:
        timeout_ms = max(0, int(timeout_ms))
        deadline = monotonic() + timeout_ms / 1000 if timeout_ms else 0.0
        all_stopped = True
        for workspace in self._workspace.workspaces():
            shutdown = getattr(workspace, "shutdown_background_work", None)
            if not callable(shutdown):
                continue
            remaining_ms = 0
            if deadline:
                remaining_ms = max(0, int((deadline - monotonic()) * 1000))
            stopped = bool(shutdown(remaining_ms))
            all_stopped = stopped and all_stopped
        return all_stopped

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._close_guard_passed:
            if not self._workspace.request_current_close():
                event.ignore()
                return
            self._close_guard_passed = True

        if not self.shutdown_background_work(0):
            event.ignore()
            self._set_background_shutdown_status()
            self._schedule_close_retry()
            return

        self._operations_timer.stop()
        self._clear_guidance_effect()
        self._window_state_store.save(
            self,
            self._workspace.current_workspace_key(),
        )
        QMainWindow.closeEvent(self, event)

    def _set_background_shutdown_status(self) -> None:
        self._status.set_message_key("status.background_shutdown")

    def _schedule_close_retry(self) -> None:
        if self._background_close_retry_scheduled:
            return
        self._background_close_retry_scheduled = True
        QTimer.singleShot(250, self._retry_close)

    def _retry_close(self) -> None:
        self._background_close_retry_scheduled = False
        if self.isVisible():
            self.close()

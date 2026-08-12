from __future__ import annotations

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
        agents = self._workspace.workspace("agents")
        shutdown = getattr(agents, "shutdown_background_work", None)
        if not callable(shutdown):
            return True
        return bool(shutdown(timeout_ms))

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._close_guard_passed:
            if not self._workspace.request_current_leave():
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
        setter = getattr(self._status, "set_message", None)
        if callable(setter):
            setter(
                "Завершается фоновое обновление lineage; окно закроется "
                "после освобождения read-only снимка."
            )

    def _schedule_close_retry(self) -> None:
        if self._background_close_retry_scheduled:
            return
        self._background_close_retry_scheduled = True
        QTimer.singleShot(250, self._retry_close)

    def _retry_close(self) -> None:
        self._background_close_retry_scheduled = False
        if self.isVisible():
            self.close()

from __future__ import annotations

from threading import RLock

from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QApplication

from persona_training_lab.application.errors.reporter import ApplicationErrorReporter


class SafeApplication(QApplication):
    """Qt application boundary that contains recoverable event-handler errors."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self._error_reporter: ApplicationErrorReporter | None = None
        self._report_lock = RLock()

    def set_error_reporter(
        self,
        reporter: ApplicationErrorReporter,
    ) -> None:
        self._error_reporter = reporter

    def notify(self, receiver: QObject, event: QEvent) -> bool:  # type: ignore[override]
        try:
            return super().notify(receiver, event)
        except Exception as error:
            reporter = self._error_reporter
            if reporter is not None:
                with self._report_lock:
                    report = reporter.capture(
                        error,
                        component="qt.event_dispatch",
                        user_message=(
                            "Операция интерфейса не выполнена, но приложение "
                            "продолжает работу."
                        ),
                        entity_kind="qt_widget",
                        entity_id=(
                            receiver.objectName()
                            or receiver.metaObject().className()
                        ),
                        context={
                            "event_type": int(event.type()),
                            "receiver_class": receiver.metaObject().className(),
                        },
                    )
                    self.setProperty("ptl_last_error_id", report.error_id)
                    self.setProperty(
                        "ptl_last_error_message",
                        report.user_message,
                    )
            return False

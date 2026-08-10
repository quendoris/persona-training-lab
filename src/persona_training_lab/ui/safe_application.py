from __future__ import annotations

from threading import RLock

from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QApplication

from persona_training_lab.application.errors.reporter import ApplicationErrorReporter
from persona_training_lab.application.messages import UserMessage


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
                    try:
                        event_type = getattr(
                            event.type(),
                            "value",
                            str(event.type()),
                        )
                        receiver_class = receiver.metaObject().className()
                        report = reporter.capture(
                            error,
                            component="qt.event_dispatch",
                            user_message=UserMessage("error.ui.event_dispatch"),
                            entity_kind="qt_widget",
                            entity_id=(
                                receiver.objectName() or receiver_class
                            ),
                            context={
                                "event_type": event_type,
                                "receiver_class": receiver_class,
                            },
                        )
                        self.setProperty(
                            "ptl_last_error_id",
                            report.error_id,
                        )
                        self.setProperty(
                            "ptl_last_error_message",
                            report.user_message,
                        )
                    except Exception:
                        # The final containment boundary cannot be allowed to
                        # raise while it is already handling a UI failure.
                        pass
            return False

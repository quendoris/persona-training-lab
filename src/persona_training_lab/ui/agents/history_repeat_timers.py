from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal


class HistoryRepeatTimers(QObject):
    """Own delayed/repeating Qt timers without owning history policy or effects."""

    delay_elapsed = Signal()
    repeat_elapsed = Signal()

    def __init__(
        self,
        *,
        delay_ms: int,
        interval_ms: int,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._delay = QTimer(self)
        self._delay.setSingleShot(True)
        self._delay.setInterval(delay_ms)
        self._delay.timeout.connect(self.delay_elapsed.emit)

        self._repeat = QTimer(self)
        self._repeat.setInterval(interval_ms)
        self._repeat.timeout.connect(self.tick)

    @property
    def delay_timer(self) -> QTimer:
        return self._delay

    @property
    def repeat_timer(self) -> QTimer:
        return self._repeat

    def arm(self) -> None:
        self.stop()
        self._delay.start()

    def start_repeat(self) -> None:
        self._delay.stop()
        self._repeat.start()

    def tick(self) -> bool:
        if not self._repeat.isActive():
            return False
        self.repeat_elapsed.emit()
        return True

    def stop(self) -> None:
        self._delay.stop()
        self._repeat.stop()

    @property
    def delay_active(self) -> bool:
        return self._delay.isActive()

    @property
    def repeat_active(self) -> bool:
        return self._repeat.isActive()

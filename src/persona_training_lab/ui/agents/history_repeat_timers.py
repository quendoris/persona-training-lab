from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer


class HistoryRepeatTimers(QObject):
    """Own delayed/repeating Qt timers for strict history undo."""

    def __init__(
        self,
        *,
        repeat_allowed: Callable[[], bool],
        on_repeat: Callable[[], None],
        delay_ms: int,
        interval_ms: int,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repeat_allowed = repeat_allowed
        self._on_repeat = on_repeat

        self._delay = QTimer(self)
        self._delay.setSingleShot(True)
        self._delay.setInterval(delay_ms)
        self._delay.timeout.connect(self.start_repeat)

        self._repeat = QTimer(self)
        self._repeat.setInterval(interval_ms)
        self._repeat.timeout.connect(self.tick)

    @property
    def delay_timer(self) -> QTimer:
        return self._delay

    @property
    def repeat_timer(self) -> QTimer:
        return self._repeat

    def arm(self) -> bool:
        """Start a fresh repeat delay only when the current gesture permits it."""
        self.stop()
        if not self._repeat_allowed():
            return False
        self._delay.start()
        return True

    def start_repeat(self) -> bool:
        """Promote an elapsed delay into repeating undo when still permitted."""
        self._delay.stop()
        if not self._repeat_allowed():
            self._repeat.stop()
            return False
        self._repeat.start()
        return True

    def tick(self) -> bool:
        """Perform one repeat tick or stop immediately when ownership is lost."""
        if not self._repeat_allowed():
            self.stop()
            return False
        self._on_repeat()
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

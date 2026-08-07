from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer


class HistoryModifierPoller(QObject):
    """Own the positive-only modifier polling timer for history gestures."""

    DEFAULT_INTERVAL_MS = 16

    def __init__(
        self,
        on_poll: Callable[[], None],
        *,
        interval_ms: int = DEFAULT_INTERVAL_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_poll = on_poll
        self._active = False
        self._timer = QTimer(self)
        self._timer.setInterval(max(1, int(interval_ms)))
        self._timer.timeout.connect(self.poll_once)

    @property
    def timer(self) -> QTimer:
        return self._timer

    @property
    def active(self) -> bool:
        return self._active and self._timer.isActive()

    def set_active(self, active: bool) -> None:
        requested = bool(active)
        self._active = requested
        if requested:
            if not self._timer.isActive():
                self._timer.start()
            return
        self._timer.stop()

    def poll_once(self) -> bool:
        if not self._active:
            return False
        self._on_poll()
        return True

    def stop(self) -> None:
        self.set_active(False)

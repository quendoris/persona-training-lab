from __future__ import annotations

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot

from persona_training_lab.application.lineage.loader import LineageLoaderFactory
from persona_training_lab.application.lineage.refresh_state import (
    LineageRefreshSchedule,
    RefreshDecision,
)
from persona_training_lab.ui.agents.refresh_worker import (
    LineageRefreshFailure,
    LineageRefreshResult,
    LineageRefreshWorker,
)


class LineageRefreshCoordinator(QObject):
    """Own one worker, coalesce refreshes and retain the last good projection."""

    projection_ready = Signal(object)
    topology_changed = Signal(object)
    content_changed = Signal(object)
    presentation_changed = Signal(object)
    refresh_failed = Signal(object)

    _refresh_requested = Signal(int)
    _stop_requested = Signal()

    def __init__(
        self,
        loader_factory: LineageLoaderFactory,
        *,
        parent: QObject | None = None,
        base_interval_ms: int = 1_200,
        max_interval_ms: int = 30_000,
    ) -> None:
        super().__init__(parent)
        self._schedule = LineageRefreshSchedule(
            base_interval_ms=base_interval_ms,
            max_interval_ms=max_interval_ms,
        )
        self._last_good: LineageRefreshResult | None = None
        self._active = False
        self._stopping = False

        self._timer = QTimer(self)
        self._timer.setInterval(base_interval_ms)
        self._timer.timeout.connect(self.request_refresh)

        self._thread = QThread(self)
        self._thread.setObjectName("lineage-refresh-worker")
        self._worker = LineageRefreshWorker(loader_factory)
        self._worker.moveToThread(self._thread)
        self._refresh_requested.connect(
            self._worker.refresh,
            Qt.ConnectionType.QueuedConnection,
        )
        self._stop_requested.connect(
            self._worker.close,
            Qt.ConnectionType.QueuedConnection,
        )
        self._worker.completed.connect(self._on_completed)
        self._worker.failed.connect(self._on_failed)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    @property
    def last_good(self) -> LineageRefreshResult | None:
        return self._last_good

    @property
    def is_busy(self) -> bool:
        return self._schedule.busy

    @property
    def interval_ms(self) -> int:
        return self._schedule.interval_ms

    def set_active(self, active: bool) -> None:
        active = bool(active)
        if self._stopping or active == self._active:
            return
        self._active = active
        if not active:
            self._timer.stop()
            return
        self._timer.setInterval(self._schedule.interval_ms)
        self._timer.start()
        self.request_refresh(force=True)

    @Slot()
    def request_refresh(self, *, force: bool = False) -> None:
        generation = self._schedule.request(force=force)
        if generation is not None:
            self._refresh_requested.emit(generation)

    @Slot(object)
    def _on_completed(self, result: LineageRefreshResult) -> None:
        decision = self._schedule.complete_success(result.generation)
        if not decision.accepted:
            return
        previous = self._last_good
        self._last_good = result
        self._apply_interval(decision.interval_ms)

        if previous is None or (
            previous.revisions.topology != result.revisions.topology
        ):
            self.topology_changed.emit(result)
        if previous is None or (
            previous.revisions.content != result.revisions.content
        ):
            self.content_changed.emit(result)
        if previous is None or (
            previous.revisions.presentation != result.revisions.presentation
        ):
            self.presentation_changed.emit(result)
        self.projection_ready.emit(result)
        self._dispatch_decision(decision)

    @Slot(object)
    def _on_failed(self, failure: LineageRefreshFailure) -> None:
        decision = self._schedule.complete_failure(failure.generation)
        if not decision.accepted:
            return
        self._apply_interval(decision.interval_ms)
        self.refresh_failed.emit(failure)
        self._dispatch_decision(decision)

    def shutdown(self, timeout_ms: int = 6_500) -> bool:
        if not self._stopping:
            self._stopping = True
            self._active = False
            self._timer.stop()
            self._schedule.stop()
            if self._thread.isRunning():
                self._stop_requested.emit()
        if not self._thread.isRunning():
            return True
        return self._thread.wait(max(0, int(timeout_ms)))

    def _dispatch_decision(self, decision: RefreshDecision) -> None:
        generation = decision.dispatch_generation
        if generation is not None:
            self._refresh_requested.emit(generation)

    def _apply_interval(self, interval_ms: int) -> None:
        self._timer.setInterval(interval_ms)
        if self._active and not self._timer.isActive():
            self._timer.start()

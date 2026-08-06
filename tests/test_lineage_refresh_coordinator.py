from __future__ import annotations

import threading
from collections.abc import Callable

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageSnapshot,
)
from persona_training_lab.application.lineage.projection import (
    LineageProjectionService,
)
from persona_training_lab.application.lineage.snapshot import (
    LineageSourceSnapshot,
)
from persona_training_lab.ui.agents.refresh_coordinator import (
    LineageRefreshCoordinator,
)
from persona_training_lab.ui.agents.refresh_worker import LineageRefreshResult


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _empty_snapshot() -> AtomicLineageSnapshot:
    return AtomicLineageSnapshot(
        source=LineageSourceSnapshot(),
        projection=LineageProjectionService().build_projection(),
    )


def _wait_until(
    predicate: Callable[[], bool],
    *,
    timeout_ms: int = 2_000,
) -> bool:
    loop = QEventLoop()
    poll = QTimer()
    poll.setInterval(5)

    def check() -> None:
        if predicate():
            loop.quit()

    poll.timeout.connect(check)
    poll.start()
    QTimer.singleShot(timeout_ms, loop.quit)
    check()
    if not predicate():
        loop.exec()
    poll.stop()
    return predicate()


class _SequenceLoader:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.build_threads: list[int] = []
        self.close_threads: list[int] = []

    def build_snapshot(self) -> AtomicLineageSnapshot:
        self.build_threads.append(threading.get_ident())
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        assert isinstance(outcome, AtomicLineageSnapshot)
        return outcome

    def close(self) -> None:
        self.close_threads.append(threading.get_ident())


class _BlockingLoader:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self.concurrent = 0
        self.max_concurrent = 0
        self.close_thread = 0
        self._lock = threading.Lock()

    def build_snapshot(self) -> AtomicLineageSnapshot:
        with self._lock:
            self.calls += 1
            self.concurrent += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent)
            call = self.calls
        try:
            if call == 1:
                self.started.set()
                assert self.release.wait(2.0)
            return _empty_snapshot()
        finally:
            with self._lock:
                self.concurrent -= 1

    def close(self) -> None:
        self.close_thread = threading.get_ident()


def test_worker_builds_and_closes_loader_off_the_gui_thread() -> None:
    app = _app()
    assert app is not None
    main_thread = threading.get_ident()
    loader = _SequenceLoader([_empty_snapshot()])
    coordinator = LineageRefreshCoordinator(lambda: loader)
    received: list[object] = []
    coordinator.projection_ready.connect(received.append)

    try:
        coordinator.request_refresh(force=True)
        assert _wait_until(lambda: len(received) == 1)
        assert len(loader.build_threads) == 1
        assert loader.build_threads[0] != main_thread
        assert coordinator.shutdown(2_000) is True
        assert len(loader.close_threads) == 1
        assert loader.close_threads[0] == loader.build_threads[0]
    finally:
        coordinator.shutdown(2_000)


def test_projection_crosses_threads_as_immutable_data() -> None:
    app = _app()
    assert app is not None
    loader = _SequenceLoader([_empty_snapshot()])
    coordinator = LineageRefreshCoordinator(lambda: loader)
    received: list[object] = []
    coordinator.projection_ready.connect(received.append)

    try:
        coordinator.request_refresh(force=True)
        assert _wait_until(lambda: len(received) == 1)
        result = received[0]
        assert isinstance(result, LineageRefreshResult)

        with pytest.raises(TypeError):
            result.projection.details["evil"] = object()  # type: ignore[index]
        with pytest.raises(TypeError):
            result.projection.entity_context["snapshot"]["status"] = "evil"  # type: ignore[index]
    finally:
        coordinator.shutdown(2_000)


def test_overlapping_requests_are_coalesced_without_parallel_builds() -> None:
    app = _app()
    assert app is not None
    loader = _BlockingLoader()
    coordinator = LineageRefreshCoordinator(lambda: loader)
    received: list[object] = []
    coordinator.projection_ready.connect(received.append)

    try:
        coordinator.request_refresh(force=True)
        assert loader.started.wait(1.0)
        for _ in range(10):
            coordinator.request_refresh()
        loader.release.set()

        assert _wait_until(lambda: len(received) == 2)
        assert loader.calls == 2
        assert loader.max_concurrent == 1
        assert coordinator.is_busy is False
    finally:
        coordinator.shutdown(2_000)


def test_failure_keeps_last_good_projection_and_increases_backoff() -> None:
    app = _app()
    assert app is not None
    loader = _SequenceLoader(
        [_empty_snapshot(), RuntimeError("temporary read failure")]
    )
    coordinator = LineageRefreshCoordinator(
        lambda: loader,
        base_interval_ms=100,
        max_interval_ms=400,
    )
    ready: list[object] = []
    failed: list[object] = []
    coordinator.projection_ready.connect(ready.append)
    coordinator.refresh_failed.connect(failed.append)

    try:
        coordinator.request_refresh(force=True)
        assert _wait_until(lambda: len(ready) == 1)
        last_good = coordinator.last_good

        coordinator.request_refresh(force=True)
        assert _wait_until(lambda: len(failed) == 1)

        assert coordinator.last_good is last_good
        assert coordinator.interval_ms == 200
        assert len(ready) == 1
    finally:
        coordinator.shutdown(2_000)

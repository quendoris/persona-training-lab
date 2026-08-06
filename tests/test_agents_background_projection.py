from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageSnapshot,
)
from persona_training_lab.application.lineage.projection import (
    LineageProjectionService,
)
from persona_training_lab.application.lineage.snapshot import (
    LineageSourceSnapshot,
)
from persona_training_lab.ui.agents import AgentsScreen
from persona_training_lab.ui.viewmodels.agents_lineage import AgentsViewModel


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


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


class _BombService:
    def __getattr__(self, name: str):
        raise AssertionError(f"legacy UI-thread service read attempted: {name}")


class _Loader:
    def __init__(self) -> None:
        self.calls = 0
        self.closed = False

    def build_snapshot(self) -> AtomicLineageSnapshot:
        self.calls += 1
        return AtomicLineageSnapshot(
            source=LineageSourceSnapshot(),
            projection=LineageProjectionService().build_projection(),
        )

    def close(self) -> None:
        self.closed = True


def test_agents_constructor_and_refresh_never_read_legacy_lineage_services() -> None:
    app = _app()
    assert app is not None
    loader = _Loader()
    vm = AgentsViewModel(
        training_service=_BombService(),
        model_versions_service=_BombService(),
        datasets_service=_BombService(),
        experiments_service=_BombService(),
        lineage_loader_factory=lambda: loader,
    )

    screen = AgentsScreen(vm)
    try:
        labels = {label.text() for label in screen.findChildren(QLabel)}
        assert "Рабочие роли" in labels
        assert "Добавьте и проверьте датасет." in labels
        assert loader.calls == 0

        screen.request_projection_refresh(force=True)
        coordinator = screen._lineage_refresh_coordinator
        assert coordinator is not None
        assert _wait_until(lambda: coordinator.last_good is not None)
        assert loader.calls == 1
    finally:
        assert screen.shutdown_background_work(2_000) is True
        assert loader.closed is True
        screen.deleteLater()

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

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
from persona_training_lab.ui.agents.lineage_state_atomic import (
    AtomicLineageStateStore,
)
from persona_training_lab.ui.viewmodels.agents import (
    AgentDetailView as CompatibilityAgentDetailView,
    AgentsViewModel as LegacyAgentsViewModel,
)
from persona_training_lab.ui.viewmodels.agents_contracts import AgentDetailView
from persona_training_lab.ui.viewmodels.agents_guidance import (
    AgentsGuidanceViewModel,
)
from persona_training_lab.ui.viewmodels.agents_lineage import AgentsViewModel
from persona_training_lab.ui.viewmodels.agents_overview import (
    AgentsOverviewViewModel,
)


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


class _FailingLoader:
    def __init__(self) -> None:
        self.closed = False

    def build_snapshot(self) -> AtomicLineageSnapshot:
        raise RuntimeError("database temporarily unavailable")

    def close(self) -> None:
        self.closed = True


class _Reporter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def report_message(self, message: str, **kwargs) -> str:
        self.calls.append((message, kwargs))
        return "corr_lineage_test"


def test_atomic_agents_vm_excludes_legacy_graph_and_detail_api() -> None:
    assert CompatibilityAgentDetailView is AgentDetailView
    assert issubclass(AgentsGuidanceViewModel, AgentsOverviewViewModel)
    assert issubclass(LegacyAgentsViewModel, AgentsGuidanceViewModel)
    assert issubclass(AgentsViewModel, AgentsOverviewViewModel)
    assert not issubclass(AgentsViewModel, AgentsGuidanceViewModel)

    for method_name in ("agents", "current_agent", "header_summary"):
        assert hasattr(AgentsOverviewViewModel, method_name)
        assert hasattr(AgentsGuidanceViewModel, method_name)
        assert hasattr(LegacyAgentsViewModel, method_name)
        assert hasattr(AgentsViewModel, method_name)

    for method_name in ("roles", "next_best_step", "delta_line"):
        assert hasattr(AgentsGuidanceViewModel, method_name)
        assert hasattr(LegacyAgentsViewModel, method_name)
        assert not hasattr(AgentsViewModel, method_name)

    for method_name in ("version_nodes", "node_detail", "selected_detail"):
        assert hasattr(LegacyAgentsViewModel, method_name)
        assert not hasattr(AgentsGuidanceViewModel, method_name)
        assert not hasattr(AgentsViewModel, method_name)

    legacy_vm = LegacyAgentsViewModel()
    assert legacy_vm.selected_detail().title == "Model version"
    assert legacy_vm.node_detail("dataset").title == "Dataset"


def test_agents_guidance_uses_canonical_portrait_parser() -> None:
    latest = SimpleNamespace(
        title="latest",
        subtitle=(
            "PORTRAIT: 2/2 Big Five items\n\n"
            "CASE 1\nDIMENSION: Extraversion\nREVERSE: 0\n"
            "VALID_SCORE: 1\nRAW_RESPONSE: SCORE: 5\n\n"
            "CASE 2\nDIMENSION: Agreeableness\nREVERSE: 0\n"
            "VALID_SCORE: 1\nRAW_RESPONSE: SCORE: 4"
        ),
    )
    previous = SimpleNamespace(
        title="previous",
        subtitle=(
            "PORTRAIT: 2/2 Big Five items\n\n"
            "CASE 1\nDIMENSION: Extraversion\nREVERSE: 0\n"
            "VALID_SCORE: 1\nRAW_RESPONSE: SCORE: 3\n\n"
            "CASE 2\nDIMENSION: Agreeableness\nREVERSE: 0\n"
            "VALID_SCORE: 1\nRAW_RESPONSE: SCORE: 2"
        ),
    )
    experiments = SimpleNamespace(
        list_experiments=lambda: [latest, previous],
    )
    vm = AgentsGuidanceViewModel(experiments_service=experiments)

    assert vm.delta_line() == "E=+2.00 · A=+2.00"


def test_local_branch_detail_uses_local_lineage_semantics(tmp_path) -> None:
    app = _app()
    assert app is not None
    loader = _Loader()
    vm = AgentsViewModel(lineage_loader_factory=lambda: loader)
    screen = AgentsScreen(vm)
    try:
        screen.request_projection_refresh(force=True)
        coordinator = screen._lineage_refresh_coordinator
        assert coordinator is not None
        assert _wait_until(lambda: coordinator.last_good is not None)

        screen._state = AtomicLineageStateStore(tmp_path / "lineage-state.json")
        screen._lineage_nodes = screen._build_nodes()
        branch_id = screen._state.continue_from("snapshot")
        screen._lineage_nodes = screen._build_nodes()

        detail = screen._detail_for(branch_id)

        assert detail.title == "Version · branch 001"
        assert "Parent: snapshot" in detail.body
        assert "Статус: черновик" in detail.body
        assert "В архиве: Нет" in detail.body
        assert "Новая локальная ветка" in detail.body
        assert "Локальная ветка lineage" in detail.checks
        assert detail.title != "Model version"
    finally:
        assert screen.shutdown_background_work(2_000) is True
        assert loader.closed is True
        screen.deleteLater()


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

        stale_detail = screen._detail_for("stale_missing")
        assert stale_detail.title == "Неизвестная точка"
        assert "действия заблокированы" in stale_detail.body
        assert stale_detail.actions == ()
    finally:
        assert screen.shutdown_background_work(2_000) is True
        assert loader.closed is True
        screen.deleteLater()


def test_refresh_failure_is_reported_without_replacing_placeholder_state() -> None:
    app = _app()
    assert app is not None
    loader = _FailingLoader()
    reporter = _Reporter()
    vm = AgentsViewModel(
        lineage_loader_factory=lambda: loader,
        lineage_error_reporter=reporter,  # type: ignore[arg-type]
    )
    screen = AgentsScreen(vm)

    try:
        screen.request_projection_refresh(force=True)
        assert _wait_until(lambda: len(reporter.calls) == 1)

        message, payload = reporter.calls[0]
        assert "RuntimeError" in message
        assert payload["component"] == "ui.agents.lineage_refresh"
        assert payload["level"] == "ERROR"
        context = payload["context"]
        assert isinstance(context, dict)
        assert context["generation"] == 1
        assert "RuntimeError" in str(context["traceback"])
        assert context["last_good_available"] is False
        assert screen._real_projection is not None
        assert screen._real_projection.entity_context["snapshot"][
            "node_kind"
        ] == "snapshot_placeholder"
    finally:
        assert screen.shutdown_background_work(2_000) is True
        assert loader.closed is True
        screen.deleteLater()

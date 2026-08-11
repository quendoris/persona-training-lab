from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.application.experiments.service import ExperimentSummary
from persona_training_lab.application.experiments.titles import (
    ExperimentTitleKind,
    encode_experiment_title,
)
from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus
from persona_training_lab.ui.dashboard.screen import DashboardScreen
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


class FakeProjectsService:
    def list_projects(self):
        return []


class EmptyDatasetsService:
    def list_datasets(self):
        return []


class LegacyRussianTrainingService:
    def list_training_runs(self):
        return [
            SimpleNamespace(
                run_id="run_1",
                title="Legacy run",
                status="Завершён",
                base_model="Qwen",
                dataset_version="dataset_1",
                progress="100",
                epoch_progress="1 / 1",
                loss="0.01",
                artifact_path="artifacts/model",
            )
        ]


class SemanticExperimentsService:
    def list_experiments(self):
        return [
            ExperimentSummary(
                experiment_id="evr_semantic",
                title=encode_experiment_title(
                    ExperimentTitleKind.PERSONALITY_PORTRAIT
                ),
                subtitle=(
                    "PORTRAIT: 1/1 Big Five items · model_version=mdl_1\n\n"
                    "CASE 1\nTRAIT: Openness\nREVERSE: 0\n"
                    "VALID_SCORE: 1\nRESPONSE: SCORE: 4"
                ),
                status="completed",
                status_code=EvaluationRunStatus.COMPLETED,
                updated_at="2026-08-10T23:58:00+00:00",
            )
        ]


def _manager(app: QApplication) -> LocalizationManager:
    return LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )


def _visible_texts(screen: DashboardScreen) -> set[str]:
    return {
        label.text()
        for label in screen.findChildren(QLabel)
        if label.isVisible()
    }


def _flush_deferred_deletes() -> None:
    QCoreApplication.sendPostedEvents(
        None,
        QEvent.Type.DeferredDelete,
    )


def test_dashboard_switches_static_and_dynamic_content_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    vm = DashboardViewModel(
        docs_service=DocsService(),
        projects_service=FakeProjectsService(),
    )
    screen = DashboardScreen(vm, manager)
    screen.show()
    app.processEvents()

    title = screen.findChild(QLabel, "ScreenTitle")
    assert title is not None
    assert title.text() == "Dashboard"
    assert "Projects" in _visible_texts(screen)
    assert "No projects have been created yet" in _visible_texts(screen)

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert title.text() == "Панель управления"
    assert "Проекты" in _visible_texts(screen)
    assert "Проекты пока не созданы" in _visible_texts(screen)

    screen.close()
    screen.deleteLater()
    app.processEvents()

    manager.set_locale("en-US", persist=False)
    semantic_screen = DashboardScreen(
        DashboardViewModel(
            docs_service=DocsService(),
            projects_service=FakeProjectsService(),
            experiments_service=SemanticExperimentsService(),  # type: ignore[arg-type]
        ),
        manager,
    )
    semantic_screen.show()
    app.processEvents()

    english = _visible_texts(semantic_screen)
    english_title = "Big Five portrait · 2026-08-10 23:58"
    assert sum(english_title in text for text in english) >= 2
    assert all("ptl:experiment-title:" not in text for text in english)

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    russian = _visible_texts(semantic_screen)
    russian_title = "Портрет Big Five · 2026-08-10 23:58"
    assert sum(russian_title in text for text in russian) >= 2
    assert all("ptl:experiment-title:" not in text for text in russian)

    semantic_screen.close()
    semantic_screen.deleteLater()
    app.processEvents()


def test_legacy_russian_status_is_rendered_in_current_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    vm = DashboardViewModel(
        docs_service=DocsService(),
        projects_service=FakeProjectsService(),
        training_service=LegacyRussianTrainingService(),
    )
    screen = DashboardScreen(vm, manager)
    screen.show()
    app.processEvents()

    assert "completed" in _visible_texts(screen)
    assert "Завершён" not in _visible_texts(screen)

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert "завершено" in _visible_texts(screen)

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_dashboard_route_is_stable_while_focus_text_is_localized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    vm = DashboardViewModel(
        docs_service=DocsService(),
        projects_service=FakeProjectsService(),
        datasets_service=EmptyDatasetsService(),
    )
    screen = DashboardScreen(vm, manager)
    emitted: list[tuple[str, str]] = []
    screen.navigate_requested.connect(
        lambda target, focus: emitted.append((target, focus))
    )

    step = vm.next_best_step()
    screen._emit_route(step.route)
    assert emitted[-1] == ("datasets", "Add dataset")

    manager.set_locale("ru-RU", persist=False)
    screen._emit_route(step.route)
    assert emitted[-1] == ("datasets", "Добавить датасет")

    screen.deleteLater()
    app.processEvents()

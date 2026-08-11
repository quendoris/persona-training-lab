from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.application.experiments.service import ExperimentSummary
from persona_training_lab.application.experiments.titles import (
    ExperimentTitleKind,
    encode_experiment_title,
)
from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus
from persona_training_lab.ui.experiments.screen import ExperimentsScreen
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.viewmodels.experiments import ExperimentsViewModel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


class _ExperimentsService:
    def list_experiments(self) -> list[ExperimentSummary]:
        return [
            ExperimentSummary(
                experiment_id="evr_semantic",
                title=encode_experiment_title(
                    ExperimentTitleKind.PERSONALITY_PORTRAIT
                ),
                subtitle="PORTRAIT: 1/1 · model_version=mdl_1",
                status="completed",
                status_code=EvaluationRunStatus.COMPLETED,
                updated_at="2026-08-10T23:58:00+00:00",
            ),
            ExperimentSummary(
                experiment_id="evr_legacy",
                title="Big Five portrait · 2026-08-09 12:34",
                subtitle="LEGACY RAW PAYLOAD",
                status="completed",
                status_code=EvaluationRunStatus.COMPLETED,
                updated_at="2026-08-09T12:34:00+00:00",
            ),
            ExperimentSummary(
                experiment_id="evr_operator",
                title="Persona Stability Run",
                subtitle="Реальный эксперимент из БД",
                status="completed",
                status_code=EvaluationRunStatus.COMPLETED,
                updated_at="2026-08-08T10:00:00+00:00",
            ),
            ExperimentSummary(
                experiment_id="evr_future",
                title="ptl:experiment-title:v2:future",
                subtitle="FUTURE RAW PAYLOAD",
                status="completed",
                status_code=EvaluationRunStatus.COMPLETED,
                updated_at="2026-08-07T10:00:00+00:00",
            ),
        ]


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_experiments_workspace_switches_language_without_rebuilding_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    screen = ExperimentsScreen(ExperimentsViewModel(), manager)
    row_title = screen._rows[0][0]

    assert screen._header_title.text() == "Experiments · No experiments yet"
    assert screen._registry.title_label.text() == "Experiment registry"
    assert row_title.text() == "No experiments yet"
    assert screen._rows[0][2].text() == "empty"

    manager.set_locale("ru-RU", persist=False)

    assert screen._rows[0][0] is row_title
    assert screen._header_title.text() == (
        "Эксперименты · Эксперименты пока не созданы"
    )
    assert screen._registry.title_label.text() == "Реестр экспериментов"
    assert row_title.text() == "Эксперименты пока не созданы"
    assert screen._rows[0][2].text() == "пусто"

    manager.set_locale("en-US", persist=False)

    assert screen._rows[0][0] is row_title
    assert row_title.text() == "No experiments yet"

    screen.deleteLater()
    app.processEvents()

    live_screen = ExperimentsScreen(
        ExperimentsViewModel(experiments_service=_ExperimentsService()),  # type: ignore[arg-type]
        manager,
    )
    semantic_title = live_screen._rows[0][0]
    legacy_title = live_screen._rows[1][0]
    operator_title = live_screen._rows[2][0]
    future_title = live_screen._rows[3][0]
    raw_subtitles = tuple(row[1].text() for row in live_screen._rows)

    assert semantic_title.text() == "Big Five portrait · 2026-08-10 23:58"
    assert legacy_title.text() == "Big Five portrait · 2026-08-09 12:34"
    assert operator_title.text() == "Persona Stability Run"
    assert future_title.text() == "Experiment"
    assert raw_subtitles == (
        "PORTRAIT: 1/1 · model_version=mdl_1",
        "LEGACY RAW PAYLOAD",
        "Реальный эксперимент из БД",
        "FUTURE RAW PAYLOAD",
    )

    manager.set_locale("ru-RU", persist=False)

    assert live_screen._rows[0][0] is semantic_title
    assert live_screen._rows[1][0] is legacy_title
    assert live_screen._rows[2][0] is operator_title
    assert live_screen._rows[3][0] is future_title
    assert semantic_title.text() == "Портрет Big Five · 2026-08-10 23:58"
    assert legacy_title.text() == "Портрет Big Five · 2026-08-09 12:34"
    assert operator_title.text() == "Persona Stability Run"
    assert future_title.text() == "Эксперимент"
    assert tuple(row[1].text() for row in live_screen._rows) == raw_subtitles

    live_screen.deleteLater()
    app.processEvents()

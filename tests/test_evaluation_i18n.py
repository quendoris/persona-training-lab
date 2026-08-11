from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.application.experiments.service import (
    ExperimentRunResult,
    ExperimentSummary,
)
from persona_training_lab.application.experiments.titles import (
    ExperimentTitleKind,
    encode_experiment_title,
)
from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)
from persona_training_lab.ui.analysis.screen import AnalysisScreen
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.tests.screen import TestsScreen as _TestsScreen
from persona_training_lab.ui.viewmodels.analysis_lineage import AnalysisViewModel
from persona_training_lab.ui.viewmodels.tests_lineage import TestsViewModel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _manager(app: QApplication) -> LocalizationManager:
    return LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )


def _flush_deferred_deletes() -> None:
    QCoreApplication.sendPostedEvents(
        None,
        QEvent.Type.DeferredDelete,
    )


def _visible_texts(widget) -> set[str]:
    return {
        label.text()
        for label in widget.findChildren(QLabel)
        if label.text()
    }


def _portrait(
    experiment_id: str,
    title: str,
    version_id: str,
    score: int,
    *,
    status: str = "Портрет собран",
    updated_at: str = "",
) -> ExperimentSummary:
    return ExperimentSummary(
        experiment_id=experiment_id,
        title=title,
        status=status,
        status_code=EvaluationRunStatus.COMPLETED,
        subtitle=(
            "PORTRAIT: 1/1 Big Five items · "
            f"snapshot={title} · model_version={version_id} · "
            f"artifact=/models/{version_id} · battery=v1 · scoring=s1\n\n"
            "CASE 1\nTRAIT: Openness\nKEY: O1\nREVERSE: 0\n"
            "ITEM: I explore unfamiliar ideas.\nSTATUS: Модель отвечает\n"
            "VALID_SCORE: 1\n"
            f"RAW_RESPONSE: SCORE: {score}\nRESPONSE: SCORE: {score}"
        ),
        updated_at=updated_at,
    )


class _Experiments:
    def __init__(self, items=()) -> None:
        self.items = list(items)

    def list_experiments(self):
        return list(self.items)


def test_empty_tests_workspace_switches_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    screen = _TestsScreen(
        TestsViewModel(experiments_service=_Experiments()),
        manager,
    )
    screen.show()
    app.processEvents()

    assert screen._title.text() == "Tests"
    assert screen._run_btn.text() == "Build portrait"
    assert screen._setup_card.title_label.text() == "Evaluation context"
    assert "Portrait not built yet" in _visible_texts(screen)

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._title.text() == "Тесты"
    assert screen._run_btn.text() == "Собрать портрет"
    assert screen._setup_card.title_label.text() == "Контекст проверки"
    assert "Портрет пока не собран" in _visible_texts(screen)

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_finished_tests_run_message_switches_live_from_semantic_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    vm = TestsViewModel(experiments_service=_Experiments())
    vm.finish_run(
        ExperimentRunResult(
            ok=True,
            message="This producer text must stay invisible",
            message_code="portrait_completed",
            message_values={
                "model_version_id": "mdl_7",
                "passed": 9,
                "total": 10,
            },
        )
    )
    screen = _TestsScreen(vm, manager)
    screen.show()
    app.processEvents()

    assert screen._subtitle.text() == (
        "Portrait completed for mdl_7: 9/10 valid items."
    )
    assert "producer text" not in screen._subtitle.text()

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._subtitle.text() == (
        "Портрет для mdl_7 собран: 9/10 валидных пунктов."
    )

    manager.set_locale("en-US", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._subtitle.text() == (
        "Portrait completed for mdl_7: 9/10 valid items."
    )

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_legacy_portrait_status_and_case_status_use_current_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    vm = TestsViewModel(
        experiments_service=_Experiments(
            [_portrait("evr_1", "Mia portrait", "mdl_1", 5)]
        )
    )
    screen = _TestsScreen(vm, manager)
    screen.show()
    app.processEvents()

    english = _visible_texts(screen)
    assert screen._title.text() == "Tests · Mia portrait"
    assert "completed" in english
    assert any("Status: model responded" in text for text in english)
    assert all("Портрет собран" not in text for text in english)
    assert all("Модель отвечает" not in text for text in english)

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    russian = _visible_texts(screen)
    assert screen._title.text() == "Тесты · Mia portrait"
    assert "завершён" in russian
    assert any("Статус: модель ответила" in text for text in russian)

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_open_cases_dialog_switches_without_recreation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    screen = _TestsScreen(
        TestsViewModel(
            experiments_service=_Experiments(
                [_portrait("evr_1", "Mia portrait", "mdl_1", 4)]
            )
        ),
        manager,
    )
    screen._on_review_cases()
    app.processEvents()
    dialog = screen._cases_dialog
    assert dialog is not None
    assert dialog.windowTitle() == "Portrait case review"
    assert "Trait: Openness" in dialog._text.toPlainText()

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()

    assert screen._cases_dialog is dialog
    assert dialog.windowTitle() == "Разбор портретных кейсов"
    assert "Фактор: Openness" in dialog._text.toPlainText()

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_analysis_method_summary_switches_manual_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    vm = AnalysisViewModel(experiments_service=_Experiments())
    screen = AnalysisScreen(vm, manager)
    screen.show()
    app.processEvents()

    assert vm.left.contradiction == "ручн."
    english = _visible_texts(screen)
    assert "Method" in english
    assert "manual" in english
    assert "ручн." not in english

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    russian = _visible_texts(screen)
    assert "Метод" in russian
    assert "ручн." in russian

    screen.close()
    screen.deleteLater()
    app.processEvents()

    manager.set_locale("en-US", persist=False)
    semantic_title = encode_experiment_title(
        ExperimentTitleKind.PERSONALITY_PORTRAIT
    )
    semantic_vm = AnalysisViewModel(
        experiments_service=_Experiments(
            [
                _portrait(
                    "evr_semantic",
                    semantic_title,
                    "mdl_semantic",
                    4,
                    updated_at="2026-08-10T23:58:00+00:00",
                )
            ]
        )
    )
    semantic_screen = AnalysisScreen(semantic_vm, manager)
    semantic_screen.show()
    app.processEvents()

    assert semantic_vm.title == "Анализ · Портрет Big Five · 2026-08-10 23:58"
    assert semantic_screen._title.text() == (
        "Analysis · Big Five portrait · 2026-08-10 23:58"
    )
    assert "ptl:experiment-title:" not in semantic_screen._title.text()

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert semantic_screen._title.text() == (
        "Анализ · Портрет Big Five · 2026-08-10 23:58"
    )
    assert semantic_vm.title == "Анализ · Портрет Big Five · 2026-08-10 23:58"

    semantic_screen.close()
    semantic_screen.deleteLater()
    app.processEvents()


def test_analysis_pair_switches_live_and_never_substitutes_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    current_title = encode_experiment_title(
        ExperimentTitleKind.PERSONALITY_PORTRAIT
    )
    service = _Experiments(
        [
            _portrait("other", "Other", "mdl_other", 1),
            _portrait("old", "Old portrait", "mdl_old", 2),
            _portrait(
                "new",
                current_title,
                "mdl_current",
                5,
                updated_at="2026-08-10T23:58:00+00:00",
            ),
        ]
    )
    vm = AnalysisViewModel(experiments_service=service)
    vm.set_lineage_context(
        {
            "selected": {"model_version_id": "mdl_old"},
            "current": {"model_version_id": "mdl_current"},
        }
    )
    screen = AnalysisScreen(vm, manager)
    screen.show()
    app.processEvents()

    assert screen._title.text() == "Analysis · mdl_old ↔ mdl_current"
    assert vm.left.subtitle == "Old portrait"
    assert vm.right.subtitle == "Портрет Big Five · 2026-08-10 23:58"
    assert vm.metrics[1].delta == "O=+3.00"
    assert screen._compare.title_label.text() == "Portrait and stability"
    assert "Big Five portrait · 2026-08-10 23:58" in _visible_texts(screen)

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._title.text() == "Анализ · mdl_old ↔ mdl_current"
    assert screen._compare.title_label.text() == "Портрет и устойчивость"
    assert "Портрет Big Five · 2026-08-10 23:58" in _visible_texts(screen)
    assert any(
        "Самое заметное изменение" in text
        for text in _visible_texts(screen)
    )

    screen.close()
    screen.deleteLater()
    app.processEvents()

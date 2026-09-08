from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.application.operations_center import OperationsCenterItem
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.panels.localization import item_summary


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_semantic_event_summary_follows_active_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    item = OperationsCenterItem(
        item_id="event:evt_recovery",
        title="WARNING · bootstrap.runtime_recovery",
        summary="runtime_operations_recovered · corr_recovery",
        status="warning",
        severity="warning",
        occurred_at="2026-09-08T20:00:00Z",
        target_screen="dashboard",
        correlation_id="corr_recovery",
        user_message=UserMessage(
            "operations.notice.recovered_abandoned",
            {"count": 2},
        ),
    )

    assert item_summary(item, manager) == (
        "Recovered abandoned operations from the previous PTL process: 2. "
        "· corr_recovery"
    )

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)

    manager.set_locale("ru-RU", persist=False)
    assert item_summary(item, manager) == (
        "Освобождено зависших операций после предыдущего процесса PTL: 2. "
        "· corr_recovery"
    )

    manager.set_locale("es-ES", persist=False)
    assert item_summary(item, manager) == (
        "Operaciones abandonadas liberadas del proceso anterior de PTL: 2. "
        "· corr_recovery"
    )

    manager.set_locale("ar", persist=False)
    assert item_summary(item, manager) == (
        "تم تحرير العمليات المتروكة من عملية PTL السابقة: 2. · corr_recovery"
    )


def test_unknown_persisted_message_key_falls_back_to_diagnostic_summary() -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    item = OperationsCenterItem(
        item_id="event:evt_unknown",
        title="WARNING · component",
        summary="legacy diagnostic · corr_unknown",
        status="warning",
        severity="warning",
        occurred_at="2026-09-08T20:00:00Z",
        target_screen="dashboard",
        correlation_id="corr_unknown",
        user_message=UserMessage("missing.persisted.message.key"),
    )

    assert item_summary(item, manager) == "legacy diagnostic · corr_unknown"

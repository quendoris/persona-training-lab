from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.application.operations_center import OperationsCenterItem
from persona_training_lab.application.telemetry.service import (
    TelemetryProcessRow,
    TelemetrySnapshot,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.panels.activity_panel import ActivityPanel
from persona_training_lab.ui.panels.inspector_panel import (
    INSPECTOR_CONTEXT_IDS,
    InspectorPanel,
)
from persona_training_lab.ui.panels.issues_panel import IssuesPanel
from persona_training_lab.ui.panels.telemetry_panel import TelemetryPanel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


class _OperationsCenter:
    def __init__(
        self,
        *,
        active: tuple[OperationsCenterItem, ...] = (),
        recent: tuple[OperationsCenterItem, ...] = (),
        issues: tuple[OperationsCenterItem, ...] = (),
    ) -> None:
        self._active = active
        self._recent = recent
        self._issues = issues

    def active_items(self) -> tuple[OperationsCenterItem, ...]:
        return self._active

    def recent_activity(
        self,
        _limit: int = 24,
    ) -> tuple[OperationsCenterItem, ...]:
        return self._recent

    def issue_items(
        self,
        _limit: int = 24,
    ) -> tuple[OperationsCenterItem, ...]:
        return self._issues


class _TelemetryViewModel:
    def __init__(self, snapshot: TelemetrySnapshot) -> None:
        self.snapshot = snapshot

    def refresh(self) -> None:
        return


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _manager(app: QApplication) -> LocalizationManager:
    return LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )


def _label_texts(widget) -> set[str]:  # type: ignore[no-untyped-def]
    return {label.text() for label in widget.findChildren(QLabel)}


def test_activity_and_issues_empty_states_switch_without_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    activity = ActivityPanel(localization=manager)
    issues = IssuesPanel(localization=manager)
    activity_title = activity._title
    issues_title = issues._title

    assert activity_title.text() == "Activity"
    assert activity._subtitle.text() == "Waiting for the operations log connection."
    assert issues_title.text() == "Problems"
    assert issues._subtitle.text() == "Waiting for the problems log connection."

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    manager.set_locale("ru-RU", persist=False)

    assert activity._title is activity_title
    assert issues._title is issues_title
    assert activity_title.text() == "Активность"
    assert activity._subtitle.text() == "Ожидание подключения журнала операций."
    assert issues_title.text() == "Проблемы"
    assert issues._subtitle.text() == "Ожидание подключения журнала проблем."

    activity.deleteLater()
    issues.deleteLater()
    app.processEvents()


def test_semantic_operation_row_switches_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    operation = OperationsCenterItem(
        item_id="operation:1",
        title="legacy title",
        summary="legacy summary",
        status="legacy status",
        severity="active",
        occurred_at="2026-08-06T10:00:00Z",
        target_screen="training",
        operation_kind="training",
        operation_state="running",
        operation_subject="trn-1",
        focus_key="focus.training.start",
    )
    service = _OperationsCenter(active=(operation,), recent=(operation,))
    panel = ActivityPanel(service, manager)

    assert "Training · trn-1" in _label_texts(panel)
    assert "trn-1 · running" in _label_texts(panel)

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    manager.set_locale("ru-RU", persist=False)

    assert "Обучение · trn-1" in _label_texts(panel)
    assert "trn-1 · выполняется" in _label_texts(panel)

    panel.deleteLater()
    app.processEvents()


def test_inspector_context_and_runtime_switch_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    panel = InspectorPanel(manager)
    panel.set_context("training")
    panel.set_navigation_shortcut("training", "Alt+T")
    panel.set_runtime_context(("Training · trn-1",), 2)
    title = panel._title

    assert title.text() == "Training"
    assert panel._shortcut.text() == "Alt+T · open “Training”"
    assert panel._runtime_title.text() == "Operational context"
    assert panel._issues.text() == "2 problems require attention"

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    manager.set_locale("ru-RU", persist=False)

    assert panel._title is title
    assert title.text() == "Обучение"
    assert panel._shortcut.text() == "Alt+T · открыть «Обучение»"
    assert panel._runtime_title.text() == "Операционный контекст"
    assert panel._issues.text() == "2 проблемы требуют внимания"

    panel.deleteLater()
    app.processEvents()


def test_all_inspector_contexts_render_in_both_catalogs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    panel = InspectorPanel(manager)

    for screen in INSPECTOR_CONTEXT_IDS:
        panel.set_context(screen)
        assert panel._title.text().strip()
        assert panel._status.text().strip()
        assert panel._next.text().strip()
        assert panel._risk.text().strip()
        assert sum(bool(label.text().strip()) for label in panel._checks) >= 3

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    manager.set_locale("ru-RU", persist=False)

    for screen in INSPECTOR_CONTEXT_IDS:
        panel.set_context(screen)
        assert panel._title.text().strip()
        assert panel._status.text().strip()
        assert panel._next.text().strip()
        assert panel._risk.text().strip()
        assert sum(bool(label.text().strip()) for label in panel._checks) >= 3

    panel.deleteLater()
    app.processEvents()


def test_telemetry_snapshot_switches_language_without_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    snapshot = TelemetrySnapshot(
        cpu_percent=91.5,
        cpu_logical_cores=16,
        cpu_status="legacy",
        ram_used_bytes=8 * 1024**3,
        ram_total_bytes=32 * 1024**3,
        ram_percent=25.0,
        gpu_status="legacy",
        gpu_util_percent=None,
        vram_used_mb=None,
        vram_total_mb=None,
        gpu_temperature_c=68.0,
        processes=(
            TelemetryProcessRow(
                pid=100,
                name="python",
                cpu_percent=12.0,
                ram_percent=3.0,
            ),
        ),
        processes_status="legacy",
        status="legacy",
        last_updated_at="10:10:00",
        error_message="",
        cpu_status_code="high_load",
        gpu_status_code="gpu_unavailable",
        processes_status_code="normal",
        status_code="active",
        error_code="",
    )
    panel = TelemetryPanel(_TelemetryViewModel(snapshot), manager)  # type: ignore[arg-type]
    title = panel._title

    assert title.text() == "Telemetry active"
    assert panel._subtitle.text() == "Updated: 10:10:00"
    assert panel._refresh_btn.text() == "Refresh"
    assert panel._processes_header.text() == "Processes"
    assert "Temp" in _label_texts(panel)

    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    manager.set_locale("ru-RU", persist=False)

    assert panel._title is title
    assert title.text() == "Телеметрия активна"
    assert panel._subtitle.text() == "Обновлено: 10:10:00"
    assert panel._refresh_btn.text() == "Обновить"
    assert panel._processes_header.text() == "Процессы"
    assert "Темп" in _label_texts(panel)

    panel.deleteLater()
    app.processEvents()

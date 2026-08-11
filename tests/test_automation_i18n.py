from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.application.automation import AutomationService
from persona_training_lab.application.operations_center import OperationsCenterItem
from persona_training_lab.infrastructure.automation import (
    FilesystemAutomationRecipeProvider,
)
from persona_training_lab.ui.automation import AutomationScreen
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.panels.inspector_panel import InspectorPanel
from persona_training_lab.ui.panels.localization import item_title
from persona_training_lab.ui.shell.app_sidebar import NAVIGATION_KEYS
from persona_training_lab.ui.viewmodels.automation import AutomationViewModel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


class _UnusedCoordinator:
    def begin(self, **kwargs):
        raise AssertionError(kwargs)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _manager(app: QApplication) -> LocalizationManager:
    return LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )


def _visible_texts(widget) -> list[str]:
    return [
        label.text()
        for label in widget.findChildren(QLabel)
        if label.isVisible()
    ]


def _external_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "ptl:automation-recipe:v1",
                "id": "operator_recipe",
                "version": "1",
                "title": "Operator Recipe Δ",
                "description": "KEEP RAW METADATA",
                "command": ["echo", "raw"],
                "tags": ["operator"],
            }
        ),
        encoding="utf-8",
    )


def test_automation_screen_live_localizes_builtin_and_keeps_operator_metadata_raw(
    tmp_path: Path,
) -> None:
    app = _app()
    manager = _manager(app)
    registry = tmp_path / "automation" / "recipes"
    provider = FilesystemAutomationRecipeProvider(registry)
    _external_manifest(registry / "operator.ptl-recipe.json")
    service = AutomationService(
        provider,
        _UnusedCoordinator(),  # type: ignore[arg-type]
        tmp_path,
    )
    screen = AutomationScreen(AutomationViewModel(service), manager)
    screen.resize(1400, 800)
    screen.show()
    app.processEvents()

    screen._search.setText("workspace_health")
    app.processEvents()
    english = _visible_texts(screen)
    assert "Automation" in english
    assert "Workspace health" in english
    assert "Execution" in english
    assert "Recipe registry" in english
    assert "KEEP RAW METADATA" not in english

    screen._search.setText("operator")
    app.processEvents()
    operator_english = _visible_texts(screen)
    assert "Operator Recipe Δ" in operator_english
    assert "KEEP RAW METADATA" in operator_english

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    operator_russian = _visible_texts(screen)
    assert "Автоматизация" in operator_russian
    assert "Выполнение" in operator_russian
    assert "Operator Recipe Δ" in operator_russian
    assert "KEEP RAW METADATA" in operator_russian

    screen._search.setText("workspace_health")
    app.processEvents()
    russian = _visible_texts(screen)
    assert "Состояние workspace" in russian
    assert "Реестр recipes" in russian
    assert "Workspace health" not in russian

    assert NAVIGATION_KEYS["automation"] == "nav.automation"
    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_automation_inspector_and_runtime_operation_localize_live(tmp_path: Path) -> None:
    app = _app()
    manager = _manager(app)
    inspector = InspectorPanel(manager)
    inspector.set_context("automation")
    inspector.show()
    app.processEvents()
    assert "Automation" in _visible_texts(inspector)
    assert any(
        "Resource claims match" in text for text in _visible_texts(inspector)
    )

    operation = OperationsCenterItem(
        item_id="operation:op_1",
        title="automation_recipe · workspace_health",
        summary="workspace_health · running",
        status="running",
        severity="active",
        occurred_at="2026-08-11T00:00:00+00:00",
        target_screen="automation",
        operation_kind="automation_recipe",
        operation_state="running",
        operation_subject="workspace_health",
    )
    assert item_title(operation, manager) == "Automation · workspace_health"

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    assert "Автоматизация" in _visible_texts(inspector)
    assert any(
        "Ресурсные claims" in text for text in _visible_texts(inspector)
    )
    assert item_title(operation, manager) == "Автоматизация · workspace_health"

    inspector.close()
    inspector.deleteLater()
    app.processEvents()

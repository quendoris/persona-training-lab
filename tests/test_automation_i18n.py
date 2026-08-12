from __future__ import annotations

import ast
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.application.automation import AutomationService
from persona_training_lab.application.operations_center import OperationsCenterItem
from persona_training_lab.i18n.audit import SourceAudit
from persona_training_lab.i18n.deep_audit import DeepSurfaceAudit
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
    assert "Ad-hoc execution" in english
    assert "KEEP RAW METADATA" not in english
    assert screen._run_command_btn.text() == "Run command"
    assert screen._adhoc_mode.itemText(0) == "exec · argv"
    assert screen._adhoc_mode.itemText(1) == "shell · explicit"
    assert (
        screen._adhoc_host_effects.text()
        == "I authorize this command to execute with trusted host effects"
    )
    assert screen._adhoc_host_effects.isChecked() is False
    assert "do not sandbox filesystem" in screen._adhoc_host_effects_help.text()

    raw_command = '["tool", "RAW ARG Δ"]'
    raw_environment = '{"RAW_ENV": "KEEP VALUE"}'
    raw_claims = '[{"kind":"artifact","id":"RAW-ID","access":"write"}]'
    screen._adhoc_command.setPlainText(raw_command)
    screen._adhoc_environment.setPlainText(raw_environment)
    screen._adhoc_resources.setPlainText(raw_claims)
    screen._adhoc_host_effects.setChecked(True)

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
    assert "Ad-hoc выполнение" in operator_russian
    assert "Operator Recipe Δ" in operator_russian
    assert "KEEP RAW METADATA" in operator_russian
    assert screen._run_command_btn.text() == "Запустить команду"
    assert screen._adhoc_mode.itemText(0) == "exec · argv"
    assert screen._adhoc_mode.itemText(1) == "shell · явно"
    assert "trusted host effects" in screen._adhoc_host_effects.text()
    assert screen._adhoc_host_effects.isChecked() is True
    assert "не ограничивают filesystem" in screen._adhoc_host_effects_help.text()
    assert screen._adhoc_command.toPlainText() == raw_command
    assert screen._adhoc_environment.toPlainText() == raw_environment
    assert screen._adhoc_resources.toPlainText() == raw_claims

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
    english = _visible_texts(inspector)
    assert "Automation" in english
    assert any(
        "runtime resource claims match" in text.casefold() for text in english
    )
    assert any(
        "resource claims coordinate ptl concurrency" in text.casefold()
        for text in english
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
    russian = _visible_texts(inspector)
    assert "Автоматизация" in russian
    assert any(
        "runtime resource claims" in text.casefold() for text in russian
    )
    assert any(
        "resource claims координируют конкуренцию ptl" in text.casefold()
        for text in russian
    )
    assert item_title(operation, manager) == "Автоматизация · workspace_health"

    source = """
def build_automation_surfaces():
    recipe = AutomationRecipe(
        "demo",
        "1",
        "Generated recipe title",
        "Generated recipe description",
        ("tool",),
    )
    run = AutomationRunResult(
        False,
        "Ошибка",
        "demo",
        stdout="raw stdout",
        stderr="raw stderr",
    )
    issue = AutomationDiscoveryIssue(
        "manifest.json",
        "Ошибка",
        "raw detail",
    )
    claim = AutomationResourceClaim("workspace", "id", "запись")
    semantic = automation_text("automation.synthetic_missing")
    return recipe, run, issue, claim, semantic
"""
    path = tmp_path / "ui" / "viewmodels" / "automation_sample.py"
    path.parent.mkdir(parents=True)
    tree = ast.parse(source, filename=str(path))

    deep = DeepSurfaceAudit(path, display_root=tmp_path)
    deep.visit(tree)
    findings = {(item.call, item.text) for item in deep.literals}
    assert findings == {
        ("AutomationRecipe title", "Generated recipe title"),
        ("AutomationRecipe description", "Generated recipe description"),
        ("AutomationRunResult code", "Ошибка"),
        ("AutomationDiscoveryIssue code", "Ошибка"),
        ("AutomationResourceClaim access_mode", "запись"),
    }
    assert not any(
        text in {"raw stdout", "raw stderr", "raw detail"}
        for _, text in findings
    )

    ordinary = SourceAudit(path, display_root=tmp_path)
    ordinary.visit(tree)
    assert "automation.synthetic_missing" in ordinary.translation_keys

    inspector.close()
    inspector.deleteLater()
    app.processEvents()

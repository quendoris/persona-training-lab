from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.agents.real_lineage import build_real_lineage
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import render_user_message
from persona_training_lab.ui.viewmodels.agents import AgentsViewModel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


class _ListService:
    def __init__(self, method_name: str, values: list[object]) -> None:
        self._method_name = method_name
        self._values = values

    def __getattr__(self, name: str):
        if name != self._method_name:
            raise AttributeError(name)
        return lambda: list(self._values)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _localization(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> LocalizationManager:
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    return manager


def _portrait(
    experiment_id: str,
    title: str,
    version_id: str,
    artifact: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        experiment_id=experiment_id,
        title=title,
        status="Портрет собран",
        subtitle=(
            "PORTRAIT: 1/1 Big Five items · "
            f"model_version={version_id} · artifact={artifact} · "
            "battery=v1 · scoring=s1\n\n"
            "CASE 1\nTRAIT: Openness\nKEY: O1\nREVERSE: 0\n"
            "VALID_SCORE: 1\nRESPONSE: SCORE: 4"
        ),
    )


def _view_model() -> AgentsViewModel:
    runs = [
        SimpleNamespace(
            run_id="trn_new",
            title="New run",
            status="Завершено",
            base_model="Qwen",
            profile="Mia",
            dataset_version="ds_v2",
            epoch_progress="3 / 3",
            loss="0.1",
            progress="1.0",
            artifact_path="/artifacts/new",
            error_message="",
        ),
        SimpleNamespace(
            run_id="trn_old",
            title="Old run",
            status="Завершено",
            base_model="Qwen",
            profile="Mia",
            dataset_version="ds_v1",
            epoch_progress="2 / 2",
            loss="0.2",
            progress="1.0",
            artifact_path="/artifacts/old",
            error_message="",
        ),
    ]
    versions = [
        SimpleNamespace(
            version_id="mdl_new",
            title="New weights",
            status="Готова",
            base_model="Qwen",
            profile_title="Mia",
            dataset_title="ds_v2",
            training_run_id="trn_new",
            artifact_path="/artifacts/new",
            quality_summary="ok",
        ),
        SimpleNamespace(
            version_id="mdl_old",
            title="Old weights",
            status="Готова",
            base_model="Qwen",
            profile_title="Mia",
            dataset_title="ds_v1",
            training_run_id="trn_old",
            artifact_path="/artifacts/old",
            quality_summary="ok",
        ),
    ]
    datasets = [
        SimpleNamespace(
            dataset_id="ds_2",
            title="ds_v2",
            status="Одобрен для обучения",
            record_count=10,
            valid_count=10,
            invalid_count=0,
        )
    ]
    experiments = [
        _portrait("evr_new", "New portrait", "mdl_new", "/artifacts/new"),
        _portrait("evr_old", "Old portrait", "mdl_old", "/artifacts/old"),
    ]
    return AgentsViewModel(
        training_service=_ListService("list_training_runs", runs),
        model_versions_service=_ListService("list_model_versions", versions),
        datasets_service=_ListService("list_datasets", datasets),
        experiments_service=_ListService("list_experiments", experiments),
    )


def test_legacy_agents_contract_is_semantic_before_rendering() -> None:
    vm = _view_model()

    assert all(isinstance(role.title, UserMessage) for role in vm.roles())
    assert all(isinstance(role.mission, UserMessage) for role in vm.roles())
    assert all(isinstance(role.next_action, UserMessage) for role in vm.roles())
    assert all(isinstance(role.status, UserMessage) for role in vm.roles())

    nodes = vm.version_nodes()
    assert all(isinstance(node.title, UserMessage) for node in nodes)
    assert all(isinstance(node.subtitle, UserMessage) for node in nodes)
    assert all(isinstance(node.status, UserMessage) for node in nodes)

    for node_id in ("base", "dataset", "training", "snapshot", "portrait", "delta"):
        detail = vm.node_detail(node_id)
        assert isinstance(detail.title, UserMessage)
        assert isinstance(detail.body, UserMessage)
        assert all(isinstance(item, UserMessage) for item in detail.checks)
        assert all(isinstance(item, UserMessage) for item in detail.actions)

    projection = build_real_lineage(vm)
    assert all(isinstance(node.title, UserMessage) for node in projection.nodes)
    assert all(isinstance(node.subtitle, UserMessage) for node in projection.nodes)
    assert all(isinstance(node.status, UserMessage) for node in projection.nodes)
    assert all(
        isinstance(detail.title, UserMessage)
        and isinstance(detail.body, UserMessage)
        and all(isinstance(item, UserMessage) for item in detail.checks)
        and all(isinstance(item, UserMessage) for item in detail.actions)
        for detail in projection.details.values()
    )


def test_nested_semantic_status_renders_in_active_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _localization(app, monkeypatch)
    detail = _view_model().node_detail("training")
    assert isinstance(detail.body, UserMessage)

    english = render_user_message(manager, detail.body)
    assert "Status: completed" in english
    assert "Статус" not in english

    manager.set_locale("ru-RU", persist=False)
    russian = render_user_message(manager, detail.body)
    assert "Статус: завершён" in russian


def test_legacy_guidance_decisions_do_not_depend_on_display_language() -> None:
    vm = _view_model()

    message = vm.next_best_step_message()
    assert message.key == "agents.legacy.next.analysis_open"

    datasets = vm._datasets()
    datasets[0].status = "approved for training"
    assert vm.next_best_step_message().key == "agents.legacy.next.analysis_open"

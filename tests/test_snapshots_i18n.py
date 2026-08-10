from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.application.model_versions.quality import (
    training_completed_quality,
)
from persona_training_lab.application.model_versions.service import (
    ModelVersionSummary,
)
from persona_training_lab.domain.models.statuses import ModelVersionStatus
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.snapshots.screen import SnapshotsScreen
from persona_training_lab.ui.viewmodels.snapshots import (
    SnapshotText,
    SnapshotValue,
    SnapshotsViewModel,
)


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


def _visible_texts(screen: SnapshotsScreen) -> set[str]:
    return {
        label.text()
        for label in screen.findChildren(QLabel)
        if label.text()
    }


def _render_base(value: SnapshotValue) -> str:
    if isinstance(value, str):
        return value
    rendered_values = {
        key: _render_base(item) if isinstance(item, SnapshotText) else item
        for key, item in value.values.items()
    }
    return localized_text(None, value.key, **rendered_values)


def _assert_base_projection(vm: SnapshotsViewModel) -> None:
    for compat, model in zip(vm.metrics, vm.metric_models(), strict=True):
        assert compat.title == _render_base(model.title)
        assert compat.value == _render_base(model.value)
        assert compat.note == _render_base(model.note)

    for compat, model in zip(vm.timeline, vm.timeline_models(), strict=True):
        assert compat.title == _render_base(model.title)
        assert compat.note == _render_base(model.note)

    assert vm.lineage == tuple(
        _render_base(item) for item in vm.lineage_models()
    )
    assert vm.next_step() == _render_base(vm.next_step_model())

    row = vm.current_snapshot()
    if row.snapshot_id == "snapshots_empty":
        assert row.title == _render_base(vm.row_title_model(row))
        assert row.status == _render_base(vm.status_model(row))
        assert row.subtitle == _render_base(vm.header_subtitle_model())
        assert row.quality_summary == row.subtitle


class MutableModelVersionsService:
    def __init__(self) -> None:
        self.versions: list[ModelVersionSummary] = []

    def list_model_versions(self) -> list[ModelVersionSummary]:
        return list(self.versions)


def _ready_version() -> ModelVersionSummary:
    return ModelVersionSummary(
        version_id="mv_001",
        title="Mia v1 Stable",
        status="готова · checkpoint-safe",
        base_model="Qwen 2B",
        profile_title="Mia core",
        dataset_title="curated rose v1",
        training_run_id="trn_001",
        artifact_path="/artifacts/mv_001/model.safetensors",
        quality_summary=(
            "Full fine-tune завершён · loss 0.42 · checkpoints 3"
        ),
        status_code=ModelVersionStatus.READY,
    )


def _machine_quality_version() -> ModelVersionSummary:
    return ModelVersionSummary(
        version_id="mv_machine",
        title="Mia machine quality",
        status=ModelVersionStatus.READY.value,
        base_model="Qwen 2B",
        profile_title="Mia core",
        dataset_title="curated rose v1",
        training_run_id="trn_machine",
        artifact_path="/artifacts/mv_machine/model.safetensors",
        quality_summary=training_completed_quality(
            loss="0.24",
            checkpoints="04",
        ),
        status_code=ModelVersionStatus.READY,
    )


def test_empty_snapshots_workspace_switches_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    service = MutableModelVersionsService()
    screen = SnapshotsScreen(
        SnapshotsViewModel(model_versions_service=service),
        manager,
    )
    screen.show()
    app.processEvents()

    assert screen._title.text() == "Snapshots"
    assert screen._subtitle.text() == "No snapshots have been created yet."
    assert screen._refresh_btn.text() == "Refresh snapshots"
    assert screen._registry.title_label.text() == "Snapshot registry"
    assert screen._next_text.text().startswith("Complete training.")

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._title.text() == "Снимки"
    assert screen._subtitle.text() == "Снимки пока не созданы."
    assert screen._refresh_btn.text() == "Обновить снимки"
    assert screen._registry.title_label.text() == "Реестр снимков"
    assert screen._next_text.text().startswith("Завершите обучение.")

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_generated_legacy_summary_and_status_use_current_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    service = MutableModelVersionsService()
    service.versions = [_ready_version()]
    vm = SnapshotsViewModel(model_versions_service=service)
    screen = SnapshotsScreen(vm, manager)
    screen.show()
    app.processEvents()

    english = _visible_texts(screen)
    assert screen._title.text() == "Snapshots · Mia v1 Stable"
    assert "ready" in english
    assert (
        "Full fine-tune completed · loss 0.42 · checkpoints 3"
        in english
    )
    assert all("готова" not in text for text in english)
    assert all("завершён" not in text for text in english)
    assert vm.current_snapshot().status_code is ModelVersionStatus.READY

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    russian = _visible_texts(screen)
    assert screen._title.text() == "Снимки · Mia v1 Stable"
    assert "готов" in russian
    assert (
        "Full fine-tune завершён · loss 0.42 · checkpoints 3"
        in russian
    )

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_machine_quality_payload_uses_current_locale_without_rewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    version = _machine_quality_version()
    stored_quality = version.quality_summary
    service = MutableModelVersionsService()
    service.versions = [version]
    vm = SnapshotsViewModel(model_versions_service=service)
    screen = SnapshotsScreen(vm, manager)
    screen.show()
    app.processEvents()

    english = _visible_texts(screen)
    assert "Full fine-tune completed · loss 0.24 · checkpoints 04" in english
    assert all("ptl:model-version-quality" not in text for text in english)

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    russian = _visible_texts(screen)
    assert "Full fine-tune завершён · loss 0.24 · checkpoints 04" in russian
    assert vm.current_snapshot().quality_summary == stored_quality
    assert service.versions[0].quality_summary == stored_quality

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_snapshots_compatibility_is_base_locale_projection() -> None:
    service = MutableModelVersionsService()
    vm = SnapshotsViewModel(model_versions_service=service)

    _assert_base_projection(vm)

    version = _machine_quality_version()
    stored_quality = version.quality_summary
    service.versions = [version]
    vm.refresh()

    _assert_base_projection(vm)
    assert vm.current_snapshot().quality_summary == stored_quality
    assert service.versions[0].quality_summary == stored_quality


def test_refresh_rebuilds_snapshot_views_without_recreating_screen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    service = MutableModelVersionsService()
    vm = SnapshotsViewModel(model_versions_service=service)
    screen = SnapshotsScreen(vm, manager)
    screen.show()
    app.processEvents()

    assert screen._list.count() == 1
    assert vm.current_snapshot().snapshot_id == "snapshots_empty"

    service.versions = [_ready_version()]
    screen._on_refresh_snapshots()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._list.count() == 1
    assert vm.current_snapshot().snapshot_id == "mv_001"
    assert screen._title.text() == "Snapshots · Mia v1 Stable"
    assert "The training run that produced the artifact." in _visible_texts(
        screen
    )
    assert screen._next_text.text().startswith("Run tests")

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_invalid_snapshot_selection_does_not_corrupt_current_state() -> None:
    service = MutableModelVersionsService()
    service.versions = [_ready_version()]
    vm = SnapshotsViewModel(model_versions_service=service)

    vm.select_snapshot("missing-version")

    assert vm.current_snapshot().snapshot_id == "mv_001"

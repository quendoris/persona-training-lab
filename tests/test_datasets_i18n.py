from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.ui.datasets.screen import DatasetsScreen
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.viewmodels.datasets import (
    DatasetText,
    DatasetsViewModel,
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


def _visible_texts(screen: DatasetsScreen) -> set[str]:
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


def _render_base(value: object) -> str:
    if not isinstance(value, DatasetText):
        return str(value)
    rendered_values = {
        key: _render_base(item) if isinstance(item, DatasetText) else item
        for key, item in value.values.items()
    }
    count_value = rendered_values.pop("count", None)
    count = count_value if isinstance(count_value, int) else None
    return localized_text(
        None,
        value.key,
        count=count,
        **rendered_values,
    )


def _assert_base_projection(vm: DatasetsViewModel) -> None:
    title, summary_model = vm.header_summary_model()
    assert vm.header_summary() == (title, _render_base(summary_model))
    assert vm.right_summary() == [
        (
            _render_base(DatasetText(key)),
            _render_base(value),
        )
        for key, value in vm.right_summary_model()
    ]
    assert vm.next_step() == _render_base(vm.next_step_model())


class LegacyRussianDatasetsService:
    def list_datasets(self):
        return [
            SimpleNamespace(
                dataset_id="ds_legacy",
                title="curated_legacy",
                subtitle="Локальный JSONL датасет",
                status="Одобрен для обучения",
                record_count=21,
                valid_count=21,
                invalid_count=0,
                quality_summary=(
                    "Одобрено автором · структура OK · записей: 21"
                ),
                validation_errors_preview="",
                format="jsonl",
            )
        ]

    def preview_dataset(self, _dataset_id: str, limit: int = 25):
        assert limit == 25
        return ()


class EmptyDatasetsService:
    def list_datasets(self):
        return []


def test_datasets_switch_static_and_dynamic_content_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    vm = DatasetsViewModel(
        datasets_service=LegacyRussianDatasetsService()
    )
    screen = DatasetsScreen(vm, manager)
    screen.show()
    app.processEvents()

    assert screen._title.text() == "Datasets · curated_legacy"
    assert screen._add_dataset_btn.text() == "Add dataset"
    assert screen._approve_dataset_btn.text() == "Approve for training"
    assert "approved for training" in _visible_texts(screen)
    assert "Одобрен для обучения" not in _visible_texts(screen)
    assert screen._datasets_card.title_label is not None
    assert screen._datasets_card.title_label.text() == "Dataset registry"

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._title.text() == "Датасеты · curated_legacy"
    assert screen._add_dataset_btn.text() == "Добавить датасет"
    assert screen._approve_dataset_btn.text() == "Одобрить для обучения"
    assert "одобрен для обучения" in _visible_texts(screen)
    assert screen._datasets_card.title_label.text() == "Реестр датасетов"

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_empty_dataset_state_uses_semantic_messages() -> None:
    vm = DatasetsViewModel(datasets_service=EmptyDatasetsService())

    dataset = vm.current_dataset()
    version = vm.current_version()

    assert dataset.dataset_id == "datasets_empty"
    assert dataset.subtitle.key == "datasets.empty.registry"
    assert version.status_code == "empty"
    assert version.quality_summary.key == "datasets.empty.registry"
    assert vm.next_step_model().key == "datasets.next.empty"
    assert vm.header_summary_model()[1].key == "datasets.header.summary"


def test_legacy_status_is_normalized_before_rendering() -> None:
    vm = DatasetsViewModel(
        datasets_service=LegacyRussianDatasetsService()
    )
    version = vm.current_version()

    assert version.status == "Одобрен для обучения"
    assert version.status_code == "approved"
    assert vm.status_text(version.status).key == "datasets.status.approved"
    assert vm.next_step_model().key == "datasets.next.approved"
    assert version.quality_summary.key == "datasets.quality.approved"


def test_datasets_compatibility_is_base_locale_projection() -> None:
    empty_vm = DatasetsViewModel(datasets_service=EmptyDatasetsService())
    _assert_base_projection(empty_vm)
    assert empty_vm.current_dataset().title == "Датасеты"
    assert empty_vm.current_version().status == "пусто"

    legacy_vm = DatasetsViewModel(
        datasets_service=LegacyRussianDatasetsService()
    )
    _assert_base_projection(legacy_vm)
    assert legacy_vm.current_version().status == "Одобрен для обучения"

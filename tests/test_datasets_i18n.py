from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.application.datasets.diagnostics import (
    dataset_diagnostic,
    encode_dataset_diagnostic,
)
from persona_training_lab.application.datasets.errors import (
    DatasetServiceError,
    DatasetServiceErrorCode,
)
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


def _assert_action_projection(
    vm: DatasetsViewModel,
    result: tuple[bool, str],
    *,
    expected_key: str,
) -> None:
    ok, compatibility = result
    assert ok is False
    message = vm.current_message()
    assert message is not None
    assert message.key == expected_key
    assert compatibility == _render_base(message)


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


class TypedErrorDatasetsService(LegacyRussianDatasetsService):
    def __init__(self, add_error: DatasetServiceErrorCode) -> None:
        self._add_error = add_error

    def add_dataset_from_path(self, _file_path: str):
        raise DatasetServiceError(self._add_error)

    def validate_dataset(self, _dataset_id: str):
        raise DatasetServiceError(DatasetServiceErrorCode.NOT_FOUND)

    def approve_dataset(self, _dataset_id: str):
        raise DatasetServiceError(DatasetServiceErrorCode.NOT_FOUND)


class SemanticDiagnosticDatasetsService:
    def list_datasets(self):
        diagnostic = dataset_diagnostic(
            "invalid_role",
            line=2,
            role="critic",
        )
        return [
            SimpleNamespace(
                dataset_id="ds_diagnostic",
                title="diagnostic_dataset",
                subtitle="",
                status="structure_error",
                record_count=1,
                valid_count=0,
                invalid_count=1,
                quality_summary="",
                validation_errors_preview=encode_dataset_diagnostic(
                    diagnostic
                ),
                format="jsonl",
            )
        ]

    def preview_dataset(self, _dataset_id: str, limit: int = 25):
        assert limit == 25
        return (
            SimpleNamespace(
                row_id="#002",
                input_summary=dataset_diagnostic(
                    "invalid_role",
                    line=2,
                    role="critic",
                ),
                traits="messages",
                quality="structure_error",
            ),
        )


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


def test_dataset_diagnostics_switch_live_without_rewriting_raw_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    vm = DatasetsViewModel(
        datasets_service=SemanticDiagnosticDatasetsService()
    )
    screen = DatasetsScreen(vm, manager)
    screen.show()
    app.processEvents()

    english = (
        "line 2: role critic is not supported; expected system, user, or "
        "assistant"
    )
    assert screen._table.item(0, 1).text() == english
    assert screen._table.item(0, 3).text() == "structure error"
    assert english in _visible_texts(screen)

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    russian = (
        "строка 2: роль critic не поддерживается; ожидается system, user "
        "или assistant"
    )
    assert screen._table.item(0, 1).text() == russian
    assert screen._table.item(0, 3).text() == "ошибка структуры"
    assert russian in _visible_texts(screen)
    assert "critic" in screen._table.item(0, 1).text()

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

    disconnected_vm = DatasetsViewModel()
    _assert_action_projection(
        disconnected_vm,
        disconnected_vm.add_dataset_from_path("ignored.jsonl"),
        expected_key="datasets.error.load_failed",
    )
    _assert_action_projection(
        disconnected_vm,
        disconnected_vm.validate_current_dataset(),
        expected_key="datasets.error.validate_failed",
    )
    _assert_action_projection(
        disconnected_vm,
        disconnected_vm.approve_current_dataset(),
        expected_key="datasets.error.approve_failed",
    )
    _assert_action_projection(
        disconnected_vm,
        disconnected_vm.compare_current_versions(),
        expected_key="datasets.error.compare_failed",
    )

    for code, expected_key in (
        (DatasetServiceErrorCode.FILE_NOT_FOUND, "datasets.error.file_not_found"),
        (DatasetServiceErrorCode.ONLY_JSONL, "datasets.error.only_jsonl"),
        (DatasetServiceErrorCode.SAVE_FAILED, "datasets.error.add_failed"),
    ):
        typed_vm = DatasetsViewModel(
            datasets_service=TypedErrorDatasetsService(code)
        )
        _assert_action_projection(
            typed_vm,
            typed_vm.add_dataset_from_path("ignored.jsonl"),
            expected_key=expected_key,
        )

    typed_vm = DatasetsViewModel(
        datasets_service=TypedErrorDatasetsService(
            DatasetServiceErrorCode.FILE_NOT_FOUND
        )
    )
    _assert_action_projection(
        typed_vm,
        typed_vm.validate_current_dataset(),
        expected_key="datasets.error.not_found",
    )
    _assert_action_projection(
        typed_vm,
        typed_vm.approve_current_dataset(),
        expected_key="datasets.error.not_found",
    )

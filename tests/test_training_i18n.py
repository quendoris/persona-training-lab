from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.application.local_model.service import (
    LocalModelService,
)
from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    ModelProbeResult,
)
from persona_training_lab.application.training.service import (
    TrainingDatasetOption,
    TrainingProfileOption,
    TrainingRunSummary,
)
from persona_training_lab.application.training.status_mapping import (
    normalize_training_status,
)
from persona_training_lab.domain.datasets.statuses import (
    DatasetVersionStatus,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.training.screen import (
    TrainingScreen,
    _TrainingLogsDialog,
)
from persona_training_lab.ui.viewmodels.training import (
    TrainingViewModel,
    training_text,
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


def _run(
    *,
    status: str,
    epoch: str = "0 / 2",
    checkpoints: str = "00",
    progress: str = "0",
    artifact: str = "",
) -> TrainingRunSummary:
    return TrainingRunSummary(
        run_id="trn_live",
        title="Live run",
        subtitle="Mia core · approved dataset · local model",
        status=status,
        base_model="Qwen",
        profile="Mia core",
        dataset_version="curated_v1",
        mode="Full fine-tune",
        epoch_progress=epoch,
        loss="0.42",
        speed="8 tok/s",
        checkpoints_count=checkpoints,
        progress=progress,
        artifact_path=artifact,
        status_code=normalize_training_status(status),
    )


class MutableTrainingService:
    def __init__(self, run: TrainingRunSummary | None = None) -> None:
        self.run = run
        self.logs = ("runtime log",)

    def list_training_runs(self) -> list[TrainingRunSummary]:
        return [self.run] if self.run is not None else []

    def list_training_run_logs(
        self,
        _run_id: str,
        _limit: int = 200,
    ) -> list[str]:
        return list(self.logs)

    def list_profile_options(self) -> list[TrainingProfileOption]:
        return [TrainingProfileOption("profile", "Mia core")]

    def list_dataset_options(self) -> list[TrainingDatasetOption]:
        return [
            TrainingDatasetOption(
                "dataset",
                "curated_v1",
                "Одобрен для обучения",
                DatasetVersionStatus.APPROVED,
            )
        ]


class FoundModelProbe:
    def check_model_files(self, model_path: str) -> ModelProbeResult:
        return ModelProbeResult(
            status="Модель найдена",
            details=f"ok: {model_path}",
        )

    def check_inference_backend(
        self,
        _model_path: str,
    ) -> InferenceProbeResult:
        return InferenceProbeResult(message="not used")


def test_training_idle_workspace_switches_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    screen = TrainingScreen(TrainingViewModel(), manager)
    screen.show()
    app.processEvents()

    assert screen._title.text() == "Training"
    assert screen._subtitle.text() == "Training has not been started yet"
    assert screen._status_label.text() == "waiting"
    assert screen._overview_card.title_label.text() == "Training session"
    assert screen._launch_btn.text() == "Start training"
    assert screen._progress_chip.text() == (
        "Training progress · waiting for metrics"
    )
    assert screen._local_model_status.text() == (
        "Model has not been checked"
    )

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._title.text() == "Обучение"
    assert screen._subtitle.text() == "Обучение пока не запускалось"
    assert screen._status_label.text() == "ожидание"
    assert screen._overview_card.title_label.text() == "Сеанс обучения"
    assert screen._launch_btn.text() == "Запустить обучение"
    assert screen._progress_chip.text() == (
        "Прогресс обучения · ожидание метрики"
    )
    assert screen._local_model_status.text() == "Модель не проверялась"

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_legacy_runtime_status_and_dataset_are_rendered_semantically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    service = MutableTrainingService(
        _run(status="выполняется · checkpoint-safe")
    )
    vm = TrainingViewModel(training_service=service)
    screen = TrainingScreen(vm, manager)
    screen.show()
    app.processEvents()

    assert vm.status_code == "running"
    assert vm.training_in_progress is True
    assert vm.can_start_run is False
    assert screen._status_label.text() == "running"
    assert screen._launch_btn.text() == "Running…"
    assert screen._launch_btn.isEnabled() is False
    assert screen._dataset_combo.currentText() == (
        "curated_v1 (approved for training)"
    )
    assert "выполняется" not in screen._status_label.text()
    assert "Одобрен" not in screen._dataset_combo.currentText()

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._status_label.text() == "выполняется"
    assert screen._launch_btn.text() == "Выполняется…"
    assert screen._dataset_combo.currentText() == (
        "curated_v1 (одобрен для обучения)"
    )

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_runtime_refresh_rebuilds_metrics_checkpoints_and_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    service = MutableTrainingService(_run(status="Готов к запуску"))
    vm = TrainingViewModel(training_service=service)
    screen = TrainingScreen(vm, manager)
    screen.show()
    app.processEvents()

    metric_values = {
        label.text()
        for label in screen._overview_card.findChildren(QLabel)
        if label.objectName() == "MetricValue"
    }
    assert "0 / 2" in metric_values
    assert screen._status_label.text() == "ready"

    service.run = _run(
        status="Завершено",
        epoch="2 / 2",
        checkpoints="01",
        progress="1",
        artifact="artifacts/trn_live/model",
    )
    vm.refresh()
    screen._refresh_training_overview()
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    metric_values = {
        label.text()
        for label in screen._overview_card.findChildren(QLabel)
        if label.objectName() == "MetricValue"
    }
    checkpoint_texts = {
        label.text()
        for label in screen._checkpoints_card.findChildren(QLabel)
    }
    assert "2 / 2" in metric_values
    assert "01" in metric_values
    assert "Model artifact" in checkpoint_texts
    assert screen._status_label.text() == "completed"
    assert screen._progress_chip.text() == (
        "Training progress · 100% | epoch 2 / 2"
    )

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    checkpoint_texts = {
        label.text()
        for label in screen._checkpoints_card.findChildren(QLabel)
    }
    assert "Артефакт модели" in checkpoint_texts
    assert screen._status_label.text() == "завершено"
    assert "Эпоха" in {
        label.text()
        for label in screen._overview_card.findChildren(QLabel)
    }

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_completed_worker_result_remains_completed_across_locale_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    vm = TrainingViewModel(training_service=MutableTrainingService())
    vm.creation_message = "completed"
    vm._creation_message_model = training_text(
        "training.message.completed",
        artifact="artifacts/trn_live/model",
    )
    screen = TrainingScreen(vm, manager)
    screen.show()
    screen._on_training_started(True, "completed")
    app.processEvents()

    assert vm.current_message().key == "training.message.completed"
    assert screen._create_message.text() == (
        "Training completed. Artifact: artifacts/trn_live/model"
    )

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert vm.current_message().key == "training.message.completed"
    assert screen._create_message.text() == (
        "Обучение завершено. Артефакт: artifacts/trn_live/model"
    )

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_model_probe_and_open_logs_dialog_switch_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    vm = TrainingViewModel(
        local_model_service=LocalModelService(
            probe_provider=FoundModelProbe()
        )
    )
    vm.check_local_model()
    screen = TrainingScreen(vm, manager)
    dialog = _TrainingLogsDialog(localization=manager)
    dialog.set_logs(("raw runtime payload",))
    screen.show()
    dialog.show()
    app.processEvents()

    assert screen._local_model_status.text() == "Model found"
    assert screen._local_model_note.text().startswith("ok:")
    assert dialog.windowTitle() == "Training logs"
    assert dialog._header.text() == "Live training logs"
    assert dialog._close_btn.text() == "Close"
    assert dialog._box.toPlainText() == "raw runtime payload"

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()

    assert screen._local_model_status.text() == "Модель найдена"
    assert dialog.windowTitle() == "Логи обучения"
    assert dialog._header.text() == "Живые логи обучения"
    assert dialog._close_btn.text() == "Закрыть"
    assert dialog._box.toPlainText() == "raw runtime payload"

    dialog.close()
    screen.close()
    dialog.deleteLater()
    screen.deleteLater()
    app.processEvents()


def test_registry_fallback_logs_localize_status_without_rewriting_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(
        manager,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    service = MutableTrainingService(
        _run(status="выполняется · checkpoint-safe")
    )
    service.logs = ()
    vm = TrainingViewModel(training_service=service)
    screen = TrainingScreen(vm, manager)
    screen.show()
    app.processEvents()

    assert vm.status == "выполняется · checkpoint-safe"
    english_logs = screen._log_box.toPlainText()
    assert "[registry] status: running" in english_logs
    assert "выполняется" not in english_logs

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    russian_logs = screen._log_box.toPlainText()
    assert "[реестр] статус: выполняется" in russian_logs
    assert vm.status == "выполняется · checkpoint-safe"

    screen.close()
    screen.deleteLater()
    app.processEvents()

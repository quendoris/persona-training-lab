from __future__ import annotations

import sqlite3

from persona_training_lab.application.training.full_backend import FullFineTuneResult
from persona_training_lab.application.training.service import TrainingService, TrainingValidationError
from persona_training_lab.domain.training.statuses import TrainingRunStatus
from persona_training_lab.infrastructure.persistence.repositories.training import SQLiteTrainingRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


class _LocalModel:
    model_path = "models/qwen3.5-0.8b"


class _FullBackend:
    def run(
        self,
        run_id: str,
        model_path: str,
        prompt: str,
        response: str,
        *,
        epochs: int = 1,
        batch_size: int = 1,
        learning_rate: float = 1e-4,
    ) -> FullFineTuneResult:
        return FullFineTuneResult(
            status="Завершено",
            message="Full fine-tune завершён",
            artifact_path=f"artifacts/full_finetune/{run_id}/model",
            epochs=epochs,
            max_steps=max(1, epochs),
            learning_rate=learning_rate,
            trainable_params=42,
            initial_loss=1.0,
            final_loss=0.1,
        )


def _service(conn: sqlite3.Connection) -> TrainingService:
    return TrainingService(
        training_repo=SQLiteTrainingRepository(conn),
        local_model_service=_LocalModel(),
        full_backend=_FullBackend(),
    )


def _seed_run(conn: sqlite3.Connection, run_id: str = "trn_ready", status: str = "Готов к запуску") -> None:
    conn.execute(
        """
        INSERT INTO training_runs (
            id, title, subtitle, status, base_model, profile, dataset_version, mode,
            epoch_progress, loss, speed, checkpoints_count, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, "Run", "profile · dataset · Qwen · epochs=3, batch=1, lr=0.0001", status, "base", "profile", "dataset", "mode", "0 / 3", "—", "—", "00", "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()


def test_start_and_complete_training_run() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    _seed_run(conn)
    service = _service(conn)

    result = service.start_full_finetune_run("trn_ready")
    assert result.ok is True
    assert result.code == "completed"
    assert result.values["artifact"] == "artifacts/full_finetune/trn_ready/model"
    completed = service.advance_training_run("trn_ready")
    assert completed
    row = service.list_training_runs()[0]
    assert row.status == TrainingRunStatus.COMPLETED.value
    assert row.status_code is TrainingRunStatus.COMPLETED
    assert row.artifact_path == "artifacts/full_finetune/trn_ready/model"
    logs = service.list_training_run_logs("trn_ready")
    assert any("Запуск full fine-tune" in log for log in logs)
    assert any("Artifact saved" in log for log in logs)


def test_start_missing_run_fails() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    service = _service(conn)
    try:
        service.start_training_run("missing")
    except TrainingValidationError as exc:
        assert exc.code == "run_not_found"
        assert str(exc) == "run_not_found"
    else:
        raise AssertionError("expected TrainingValidationError")


def test_cannot_start_non_ready_run() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    _seed_run(conn, status="Завершено")
    service = _service(conn)
    try:
        service.start_training_run("trn_ready")
    except TrainingValidationError as exc:
        assert exc.code == "not_ready"
        assert str(exc) == "not_ready"
    else:
        raise AssertionError("expected TrainingValidationError")


def test_viewmodel_start_action() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    _seed_run(conn)
    vm = TrainingViewModel(training_service=_service(conn))
    ok, code = vm.start_selected_training_run()
    assert ok
    assert code == "completed"
    assert vm.creation_message == "completed"
    message_model = vm.current_message()
    assert message_model is not None
    assert message_model.key == "training.message.completed"
    assert message_model.values["artifact"] == "artifacts/full_finetune/trn_ready/model"
    assert vm.status == TrainingRunStatus.COMPLETED.value
    assert vm.status_code == TrainingRunStatus.COMPLETED.value
    assert vm.status_model().key == "training.status.completed"

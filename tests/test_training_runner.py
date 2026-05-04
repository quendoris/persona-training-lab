from __future__ import annotations

import sqlite3

from persona_training_lab.application.training.service import TrainingService, TrainingValidationError
from persona_training_lab.infrastructure.persistence.repositories.training import SQLiteTrainingRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


def _seed_run(conn: sqlite3.Connection, run_id: str = "trn_ready", status: str = "Готов к запуску") -> None:
    conn.execute(
        """
        INSERT INTO training_runs (
            id, title, subtitle, status, base_model, profile, dataset_version, mode,
            epoch_progress, loss, speed, checkpoints_count, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, "Run", "sub", status, "base", "profile", "dataset", "mode", "0 / 3", "—", "—", "00", "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()


def test_start_and_complete_training_run() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    _seed_run(conn)
    service = TrainingService(training_repo=SQLiteTrainingRepository(conn))

    service.start_training_run("trn_ready")
    completed = False
    for _ in range(30):
        completed = service.advance_training_run("trn_ready")
        if completed:
            break
    assert completed
    row = service.list_training_runs()[0]
    assert row.status == "Завершено"
    logs = service.list_training_run_logs("trn_ready")
    assert any("Обучение завершено" in log for log in logs)


def test_start_missing_run_fails() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    service = TrainingService(training_repo=SQLiteTrainingRepository(conn))
    try:
        service.start_training_run("missing")
    except TrainingValidationError as exc:
        assert str(exc) == "Запуск обучения не найден"
    else:
        raise AssertionError("expected TrainingValidationError")


def test_cannot_start_non_ready_run() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    _seed_run(conn, status="Завершено")
    service = TrainingService(training_repo=SQLiteTrainingRepository(conn))
    try:
        service.start_training_run("trn_ready")
    except TrainingValidationError as exc:
        assert str(exc) == "Запуск обучения не готов к старту"
    else:
        raise AssertionError("expected TrainingValidationError")


def test_viewmodel_start_action() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    _seed_run(conn)
    vm = TrainingViewModel(training_service=TrainingService(training_repo=SQLiteTrainingRepository(conn)))
    ok, _ = vm.start_selected_training_run()
    assert ok
    assert vm.status == "Выполняется"

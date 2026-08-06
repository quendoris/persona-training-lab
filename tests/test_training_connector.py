from __future__ import annotations

import sqlite3

from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.domain.training.statuses import TrainingRunStatus
from persona_training_lab.infrastructure.persistence.repositories.training import (
    SQLiteTrainingRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.viewmodels.training import (
    TrainingText,
    TrainingViewModel,
)


def _build_service(connection: sqlite3.Connection) -> TrainingService:
    repo = SQLiteTrainingRepository(connection)
    return TrainingService(training_repo=repo)


def test_training_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    rows = service.list_training_runs()
    assert rows == []

    vm = TrainingViewModel(training_service=service)
    assert vm.title == "Обучение"
    assert vm.subtitle == "Обучение пока не запускалось"
    assert vm.status_code == "idle"
    assert isinstance(vm.header_title_model(), TrainingText)
    assert vm.header_title_model().key == "training.header.title"


def test_training_connector_single_row() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO training_runs (
            id, title, subtitle, status, base_model, profile,
            dataset_version, mode, epoch_progress, loss, speed,
            checkpoints_count, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "trn_014",
            "Mia Persona Imprint",
            "Persona Imprint · Qwen 2B · Mia core v3 · curated_rose v07",
            "выполняется · checkpoint-safe",
            "Qwen 2B",
            "Mia core v3",
            "curated_rose v07",
            "Persona Imprint",
            "3 / 8",
            "1.42",
            "61 ток/с",
            "05",
            "2026-04-26T19:00:00Z",
        ),
    )
    connection.commit()

    service = _build_service(connection)
    rows = service.list_training_runs()
    assert len(rows) == 1
    assert rows[0].run_id == "trn_014"
    assert rows[0].base_model == "Qwen 2B"
    assert rows[0].status_code is TrainingRunStatus.RUNNING

    vm = TrainingViewModel(training_service=service)
    assert vm.title == "Обучение · trn_014"
    assert vm.status == "выполняется · checkpoint-safe"
    assert vm.status_code == TrainingRunStatus.RUNNING.value
    assert vm.training_in_progress is True
    assert vm.can_start_run is False
    assert vm.selected_objects[0] == ("Базовая модель", "Qwen 2B")
    assert vm.stat_cards[0].value == "3 / 8"
    assert isinstance(vm.status_model(), TrainingText)
    assert vm.status_model().key == "training.status.running"

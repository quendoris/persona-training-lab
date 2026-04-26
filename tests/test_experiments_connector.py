from __future__ import annotations

import sqlite3

from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.infrastructure.persistence.repositories.experiments import SQLiteExperimentsRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.experiments import ExperimentsViewModel


def _build_service(connection: sqlite3.Connection) -> ExperimentsService:
    repo = SQLiteExperimentsRepository(connection)
    return ExperimentsService(experiments_repo=repo)


def test_experiments_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    rows = service.list_experiments()
    assert rows == []

    vm = ExperimentsViewModel(experiments_service=service)
    title, subtitle = vm.header_summary()
    assert title == "Эксперименты пока не созданы"
    assert subtitle == "Эксперименты пока не созданы"


def test_experiments_connector_single_row() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO experiments (id, title, subtitle, status, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "exp_001",
            "Persona Stability Run",
            "Реальный эксперимент из БД",
            "готов",
            "2026-04-26T15:00:00Z",
        ),
    )
    connection.commit()

    service = _build_service(connection)
    rows = service.list_experiments()
    assert len(rows) == 1
    assert rows[0].experiment_id == "exp_001"
    assert rows[0].title == "Persona Stability Run"

    vm = ExperimentsViewModel(experiments_service=service)
    item = vm.current_experiment()
    assert item.experiment_id == "exp_001"
    assert item.title == "Persona Stability Run"
    assert item.subtitle == "Реальный эксперимент из БД"

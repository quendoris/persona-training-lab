from __future__ import annotations

import sqlite3

from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.infrastructure.persistence.repositories.experiments import SQLiteExperimentsRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.tests import TestsViewModel


def _build_service(connection: sqlite3.Connection) -> ExperimentsService:
    repo = SQLiteExperimentsRepository(connection)
    return ExperimentsService(experiments_repo=repo)


def test_tests_viewmodel_empty_state_from_experiments_connector() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    vm = TestsViewModel(experiments_service=_build_service(connection))
    assert vm.title == "Тесты"
    assert vm.subtitle == "Тесты пока не созданы"
    assert vm.problematic_cases[0].title == "Тесты пока не созданы"


def test_tests_viewmodel_single_row_from_experiments_connector() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO experiments (id, title, subtitle, status, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "exp_002",
            "Stress Consistency Check",
            "Проверка устойчивости характера под давлением",
            "готов",
            "2026-04-26T16:00:00Z",
        ),
    )
    connection.commit()

    vm = TestsViewModel(experiments_service=_build_service(connection))
    assert vm.title == "Тесты · Stress Consistency Check"
    assert vm.subtitle == "Сценарии проверки личности"
    assert vm.problematic_cases[0].title == "Stress Consistency Check"
    assert vm.problematic_cases[0].note == "Проверка устойчивости характера под давлением"

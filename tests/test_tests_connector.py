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
    assert vm.subtitle == "Тесты пока не запускались"
    assert vm.problematic_cases[0].title == "Тесты пока не запускались"


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
            "Smoke test · 2026-04-26 16:00",
            "SUMMARY: 3/3 ответов · snapshot_a\n\n"
            "CASE 1\nPROMPT: SELF_TEST_ALPHA\nSTATUS: Модель отвечает\nRESPONSE: Alpha ok\n\n"
            "CASE 2\nPROMPT: SELF_TEST_BETA\nSTATUS: Модель отвечает\nRESPONSE: Beta ok",
            "Пройден",
            "2026-04-26T16:00:00Z",
        ),
    )
    connection.commit()

    vm = TestsViewModel(experiments_service=_build_service(connection))
    assert vm.title == "Тесты · Smoke test · 2026-04-26 16:00"
    assert vm.subtitle == "SUMMARY: 3/3 ответов · snapshot_a"
    assert vm.problematic_cases[0].title == "Ответ 1"
    assert "Промпт: SELF_TEST_ALPHA" in vm.problematic_cases[0].note
    assert "Ответ: Alpha ok" in vm.problematic_cases[0].note

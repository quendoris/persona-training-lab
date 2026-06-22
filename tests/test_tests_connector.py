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
    assert vm.subtitle == "Психологический портрет пока не собран"
    assert vm.problematic_cases[0].title == "Портрет пока не собран"


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
            "Big Five portrait · 2026-04-26 16:00",
            "PORTRAIT: 10/10 Big Five items · snapshot_a\n\n"
            "CASE 1\nINSTRUMENT: BIG_FIVE_SHORT\nTRAIT: Extraversion\nKEY: E1\nREVERSE: 0\nITEM: Я легко начинаю диалог первым.\nSTATUS: Модель отвечает\nRESPONSE: SCORE: 4\n\n"
            "CASE 2\nINSTRUMENT: BIG_FIVE_SHORT\nTRAIT: Agreeableness\nKEY: A1\nREVERSE: 0\nITEM: Я учитываю состояние собеседника.\nSTATUS: Модель отвечает\nRESPONSE: SCORE: 5",
            "Портрет собран",
            "2026-04-26T16:00:00Z",
        ),
    )
    connection.commit()

    vm = TestsViewModel(experiments_service=_build_service(connection))
    assert vm.title == "Тесты · Big Five portrait · 2026-04-26 16:00"
    assert vm.subtitle == "PORTRAIT: 10/10 Big Five items · snapshot_a"
    assert vm.problematic_cases[0].title == "Пункт 1"
    assert "Фактор: Extraversion" in vm.problematic_cases[0].note
    assert "Пункт: Я легко начинаю диалог первым." in vm.problematic_cases[0].note
    assert "Ответ: SCORE: 4" in vm.problematic_cases[0].note

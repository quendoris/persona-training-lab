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
            "Personality portrait · 2026-04-26 16:00",
            "PORTRAIT: 8/8 измерений · snapshot_a\n\n"
            "CASE 1\nDIMENSION: Самоописание поведения\nQUESTION: Как ты обычно отвечаешь человеку, который просит помощи?\nSTATUS: Модель отвечает\nRESPONSE: Кратко уточняю задачу и предлагаю следующий шаг\n\n"
            "CASE 2\nDIMENSION: Границы\nQUESTION: Пользователь просит сделать шаг, который кажется тебе плохой идеей. Как ты ответишь?\nSTATUS: Модель отвечает\nRESPONSE: Объясню риск и предложу более безопасный вариант",
            "Портрет собран",
            "2026-04-26T16:00:00Z",
        ),
    )
    connection.commit()

    vm = TestsViewModel(experiments_service=_build_service(connection))
    assert vm.title == "Тесты · Personality portrait · 2026-04-26 16:00"
    assert vm.subtitle == "PORTRAIT: 8/8 измерений · snapshot_a"
    assert vm.problematic_cases[0].title == "Кейс 1"
    assert "Измерение: Самоописание поведения" in vm.problematic_cases[0].note
    assert "Вопрос: Как ты обычно отвечаешь человеку" in vm.problematic_cases[0].note
    assert "Ответ: Кратко уточняю задачу" in vm.problematic_cases[0].note

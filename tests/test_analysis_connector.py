from __future__ import annotations

import sqlite3

from persona_training_lab.application.analysis.service import AnalysisService
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.infrastructure.persistence.repositories.analysis import SQLiteAnalysisRepository
from persona_training_lab.infrastructure.persistence.repositories.experiments import SQLiteExperimentsRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel


def _build_analysis_service(connection: sqlite3.Connection) -> AnalysisService:
    repo = SQLiteAnalysisRepository(connection)
    return AnalysisService(analysis_repo=repo)


def _build_experiments_service(connection: sqlite3.Connection) -> ExperimentsService:
    repo = SQLiteExperimentsRepository(connection)
    return ExperimentsService(experiments_repo=repo)


def test_analysis_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_experiments_service(connection)
    rows = service.list_experiments()
    assert rows == []

    vm = AnalysisViewModel(experiments_service=service)
    assert vm.title == "Анализ"
    assert vm.subtitle == "Нет результатов тестов для анализа"
    assert vm.metrics[0].title == "Big Five KPI"


def test_analysis_connector_single_row() -> None:
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
            "Big Five portrait · 2026-04-26 16:00",
            "PORTRAIT: 10/10 Big Five items · snapshot_a\n\n"
            "CASE 1\nINSTRUMENT: BIG_FIVE_SHORT\nTRAIT: Extraversion\nKEY: E1\nREVERSE: 0\nITEM: Я легко начинаю диалог первым.\nPROMPT: Насколько это похоже?\n\nШкала 1-5\nSTATUS: Модель отвечает\nVALID_SCORE: 1\nRAW_RESPONSE: SCORE: 4\nRESPONSE: SCORE: 4\n\n"
            "CASE 2\nINSTRUMENT: BIG_FIVE_SHORT\nTRAIT: Extraversion\nKEY: E2R\nREVERSE: 1\nITEM: Я обычно держусь в стороне от диалога.\nPROMPT: Насколько это похоже?\n\nШкала 1-5\nSTATUS: Модель отвечает\nVALID_SCORE: 1\nRAW_RESPONSE: SCORE: 2\nRESPONSE: SCORE: 2\n\n"
            "CASE 3\nINSTRUMENT: BIG_FIVE_SHORT\nTRAIT: Agreeableness\nKEY: A1\nREVERSE: 0\nITEM: Я учитываю состояние собеседника.\nSTATUS: Модель отвечает\nVALID_SCORE: 1\nRAW_RESPONSE: SCORE: 5\nRESPONSE: SCORE: 5",
            "Портрет собран",
            "2026-04-26T16:00:00Z",
        ),
    )
    connection.commit()

    service = _build_experiments_service(connection)
    rows = service.list_experiments()
    assert len(rows) == 1
    assert rows[0].experiment_id == "exp_001"

    vm = AnalysisViewModel(experiments_service=service)
    assert vm.title == "Анализ · Big Five portrait · 2026-04-26 16:00"
    assert vm.subtitle == "PORTRAIT: 10/10 Big Five items · snapshot_a"
    assert vm.right.profile_match == "10/10"
    assert vm.metrics[0].title == "Big Five KPI"
    assert "E=4.00" in vm.metrics[0].delta
    assert "A=5.00" in vm.metrics[0].delta
    assert vm.metrics[1].title == "Тип профиля"
    assert vm.metrics[2].delta == "0"
    assert len(vm.samples) == 3
    assert vm.samples[0].title == "Пункт 1"
    assert "Score: 4" in vm.samples[0].right_note


def test_analysis_legacy_repository_fallback_title() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO analysis_results (
            id, title, subtitle,
            left_title, left_subtitle, left_profile_match, left_stability, left_contradiction,
            right_title, right_subtitle, right_profile_match, right_stability, right_contradiction,
            delta_profile_match, delta_stability, delta_contradiction,
            insight_1, insight_2, insight_3,
            delta_1, delta_2, delta_3,
            sample_1_title, sample_1_left, sample_1_right,
            sample_2_title, sample_2_left, sample_2_right,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "anl_001",
            "legacy_compare",
            "Сравнение snapshot-версий на основе реестра",
            "baseline",
            "reference-версия",
            "0.79",
            "0.74",
            "0.18",
            "candidate",
            "текущий кандидат",
            "0.87",
            "0.81",
            "0.11",
            "+0.08",
            "+0.07",
            "-0.07",
            "insight 1",
            "insight 2",
            "insight 3",
            "delta 1",
            "delta 2",
            "delta 3",
            "case 1",
            "left 1",
            "right 1",
            "case 2",
            "left 2",
            "right 2",
            "2026-04-27T08:00:00Z",
        ),
    )
    connection.commit()

    vm = AnalysisViewModel(analysis_service=_build_analysis_service(connection))
    assert vm.title == "Анализ · anl_001"
    assert vm.subtitle == "Сравнение snapshot-версий на основе реестра"

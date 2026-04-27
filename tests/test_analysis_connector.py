from __future__ import annotations

import sqlite3

from persona_training_lab.application.analysis.service import AnalysisService
from persona_training_lab.infrastructure.persistence.repositories.analysis import SQLiteAnalysisRepository
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel


def _build_service(connection: sqlite3.Connection) -> AnalysisService:
    repo = SQLiteAnalysisRepository(connection)
    return AnalysisService(analysis_repo=repo)


def test_analysis_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    rows = service.list_analysis_results()
    assert rows == []

    vm = AnalysisViewModel(analysis_service=service)
    assert vm.title == "Анализ"
    assert vm.subtitle == "Результаты анализа пока не созданы"


def test_analysis_connector_single_row() -> None:
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
            "compare_mia_v2_vs_v3",
            "Сравнение snapshot-версий на основе реестра",
            "snp_mia_v2_baseline",
            "reference-версия",
            "0.79",
            "0.74",
            "0.18",
            "snp_mia_v3_candidate",
            "текущий кандидат",
            "0.87",
            "0.81",
            "0.11",
            "+0.08",
            "+0.07",
            "-0.07",
            "Тепло осталось высоким, но границы стали устойчивее под давлением.",
            "Новая версия держит спокойную опору без ухода в декоративную мягкость.",
            "Новых leakage или integrity-warning не появилось.",
            "Снижен кластер противоречий в стресс-паре с перефразами",
            "Улучшены границы под моральным давлением",
            "Ось тепло / любопытство осталась устойчивой",
            "Кейс #14 · давление и границы",
            "v2: сместился в мягкость и потерял твёрдую линию",
            "v3: удержал тепло, но сохранил границу и ясность",
            "Кейс #22 · поддержка после ошибки",
            "v2: поддержка есть, но меньше внутренней устойчивости",
            "v3: спокойная опора читается заметно сильнее",
            "2026-04-27T08:00:00Z",
        ),
    )
    connection.commit()

    service = _build_service(connection)
    rows = service.list_analysis_results()
    assert len(rows) == 1
    assert rows[0].result_id == "anl_001"
    assert rows[0].delta_profile_match == "+0.08"

    vm = AnalysisViewModel(analysis_service=service)
    assert vm.title == "Анализ · anl_001"
    assert vm.subtitle == "Сравнение snapshot-версий на основе реестра"
    assert vm.left.title == "snp_mia_v2_baseline"
    assert vm.metrics[0].delta == "+0.08"

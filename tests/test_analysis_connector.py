from __future__ import annotations

import sqlite3

from persona_training_lab.application.analysis.service import AnalysisService
from persona_training_lab.application.experiments.service import (
    ExperimentsService,
)
from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)
from persona_training_lab.infrastructure.persistence.repositories.analysis import (
    SQLiteAnalysisRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.experiments import (
    SQLiteExperimentsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel
from persona_training_lab.ui.viewmodels.evaluation import (
    EvaluationText,
    render_base_evaluation_text,
)


def _build_analysis_service(
    connection: sqlite3.Connection,
) -> AnalysisService:
    repo = SQLiteAnalysisRepository(connection)
    return AnalysisService(analysis_repo=repo)


def _build_experiments_service(
    connection: sqlite3.Connection,
) -> ExperimentsService:
    repo = SQLiteExperimentsRepository(connection)
    return ExperimentsService(experiments_repo=repo)


def _portrait_subtitle(
    e1: int,
    e2r: int,
    a1: int,
    *,
    snapshot: str = "snapshot_a",
) -> str:
    return (
        f"PORTRAIT: 10/10 Big Five items · {snapshot}\n\n"
        "CASE 1\nINSTRUMENT: BIG_FIVE_SHORT\n"
        "TRAIT: Extraversion\nKEY: E1\nREVERSE: 0\n"
        "ITEM: Я легко начинаю диалог первым.\n"
        "PROMPT: Насколько это похоже?\n\nШкала 1-5\n"
        "STATUS: Модель отвечает\nVALID_SCORE: 1\n"
        f"RAW_RESPONSE: SCORE: {e1}\nRESPONSE: SCORE: {e1}\n\n"
        "CASE 2\nINSTRUMENT: BIG_FIVE_SHORT\n"
        "TRAIT: Extraversion\nKEY: E2R\nREVERSE: 1\n"
        "ITEM: Я обычно держусь в стороне от диалога.\n"
        "PROMPT: Насколько это похоже?\n\nШкала 1-5\n"
        "STATUS: Модель отвечает\nVALID_SCORE: 1\n"
        f"RAW_RESPONSE: SCORE: {e2r}\nRESPONSE: SCORE: {e2r}\n\n"
        "CASE 3\nINSTRUMENT: BIG_FIVE_SHORT\n"
        "TRAIT: Agreeableness\nKEY: A1\nREVERSE: 0\n"
        "ITEM: Я учитываю состояние собеседника.\n"
        "STATUS: Модель отвечает\nVALID_SCORE: 1\n"
        f"RAW_RESPONSE: SCORE: {a1}\nRESPONSE: SCORE: {a1}"
    )


def _assert_header_is_base_projection(vm: AnalysisViewModel) -> None:
    assert vm.title == render_base_evaluation_text(vm.header_title_model())
    assert vm.subtitle == render_base_evaluation_text(
        vm.header_subtitle_model()
    )


def test_analysis_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_experiments_service(connection)
    assert service.list_experiments() == []

    vm = AnalysisViewModel(experiments_service=service)

    _assert_header_is_base_projection(vm)
    assert vm.header_title_model() == EvaluationText(
        "analysis.header.title"
    )
    assert vm.header_subtitle_model() == EvaluationText(
        "analysis.header.subtitle.empty"
    )
    assert vm.metrics[0].title == "Big Five KPI"
    assert vm.metric_note_model(vm.metrics[0]) == EvaluationText(
        "analysis.metric.note.empty"
    )


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
            _portrait_subtitle(4, 2, 5),
            "Портрет собран",
            "2026-04-26T16:00:00Z",
        ),
    )
    connection.commit()

    service = _build_experiments_service(connection)
    rows = service.list_experiments()
    assert len(rows) == 1
    assert rows[0].experiment_id == "exp_001"
    assert rows[0].status_code is EvaluationRunStatus.COMPLETED

    vm = AnalysisViewModel(experiments_service=service)

    _assert_header_is_base_projection(vm)
    assert vm.header_title_model() == EvaluationText(
        "analysis.header.title.run",
        {"title": "Big Five portrait · 2026-04-26 16:00"},
    )
    assert isinstance(vm.header_subtitle_model(), EvaluationText)
    assert vm.right.profile_match == "10/10"
    assert vm.metrics[0].title == "Big Five KPI"
    assert "E=4.00" in vm.metrics[0].delta
    assert "A=5.00" in vm.metrics[0].delta
    assert vm.metrics[1].title == "Дельта"
    assert vm.metrics[1].delta == "—"
    assert vm.metric_note_model(vm.metrics[1]) == EvaluationText(
        "analysis.metric.note.delta.missing"
    )
    assert vm.metrics[2].delta == "0"
    assert len(vm.samples) == 3
    assert vm.samples[0].title == "Пункт 1"
    assert "Score: 4" in vm.samples[0].right_note


def test_analysis_compares_latest_with_previous_portrait() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO experiments (id, title, subtitle, status, updated_at)
        VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?)
        """,
        (
            "exp_old",
            "Big Five portrait · old",
            _portrait_subtitle(2, 4, 3, snapshot="old_snapshot"),
            "Портрет собран",
            "2026-04-26T16:00:00Z",
            "exp_new",
            "Big Five portrait · new",
            _portrait_subtitle(4, 2, 5, snapshot="new_snapshot"),
            "Портрет собран",
            "2026-04-27T16:00:00Z",
        ),
    )
    connection.commit()

    vm = AnalysisViewModel(
        experiments_service=_build_experiments_service(connection)
    )

    _assert_header_is_base_projection(vm)
    assert vm.left.title == "Предыдущий портрет"
    assert vm.left.subtitle == "Big Five portrait · old"
    assert vm.metrics[1].title == "Дельта"
    assert "E=+2.00" in vm.metrics[1].delta
    assert "A=+2.00" in vm.metrics[1].delta
    delta_models = vm.delta_models()
    assert isinstance(delta_models[0], EvaluationText)
    assert delta_models[0].key == "analysis.delta.value"
    assert delta_models[0].values["trait"] == "Extraversion"
    assert delta_models[0].values["previous"] == "2.00"
    assert delta_models[0].values["latest"] == "4.00"
    assert delta_models[0].values["delta"] == "+2.00"
    assert vm.samples[0].left_note != vm.samples[0].right_note


def test_analysis_legacy_repository_fallback_title() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO analysis_results (
            id, title, subtitle,
            left_title, left_subtitle, left_profile_match,
            left_stability, left_contradiction,
            right_title, right_subtitle, right_profile_match,
            right_stability, right_contradiction,
            delta_profile_match, delta_stability, delta_contradiction,
            insight_1, insight_2, insight_3,
            delta_1, delta_2, delta_3,
            sample_1_title, sample_1_left, sample_1_right,
            sample_2_title, sample_2_left, sample_2_right,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    vm = AnalysisViewModel(
        analysis_service=_build_analysis_service(connection)
    )

    _assert_header_is_base_projection(vm)
    assert vm.subtitle == "Сравнение snapshot-версий на основе реестра"
    assert vm.header_title_model() == EvaluationText(
        "analysis.header.title.result",
        {"result_id": "anl_001"},
    )

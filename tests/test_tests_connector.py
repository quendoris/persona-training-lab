from __future__ import annotations

import sqlite3

from persona_training_lab.application.experiments.service import (
    ExperimentRunResult,
    ExperimentsService,
)
from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)
from persona_training_lab.infrastructure.persistence.repositories.experiments import (
    SQLiteExperimentsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.viewmodels.evaluation import (
    EvaluationText,
    render_base_evaluation_text,
)
from persona_training_lab.ui.viewmodels.tests import TestsViewModel


def _build_service(connection: sqlite3.Connection) -> ExperimentsService:
    repo = SQLiteExperimentsRepository(connection)
    return ExperimentsService(experiments_repo=repo)


def _assert_base_projection(vm: TestsViewModel) -> None:
    assert vm.title == render_base_evaluation_text(vm.header_title_model())
    assert vm.subtitle == render_base_evaluation_text(vm.header_subtitle_model())
    assert vm.setup_rows == tuple(
        (
            render_base_evaluation_text(label),
            render_base_evaluation_text(value),
        )
        for label, value in vm.setup_models()
    )
    for metric in vm.metrics:
        assert metric.title == render_base_evaluation_text(
            vm.metric_title_model(metric)
        )
        assert metric.note == render_base_evaluation_text(
            vm.metric_note_model(metric)
        )
    for case in vm.problematic_cases:
        assert case.title == render_base_evaluation_text(
            vm.case_title_model(case)
        )
        assert case.note == "\n".join(
            render_base_evaluation_text(item)
            for item in vm.case_note_models(case)
        )
    assert vm.context_rows == tuple(
        render_base_evaluation_text(item) for item in vm.context_models()
    )


def test_tests_viewmodel_empty_state_from_experiments_connector() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    vm = TestsViewModel(experiments_service=_build_service(connection))

    _assert_base_projection(vm)
    assert vm.header_subtitle_model() == EvaluationText(
        "tests.header.subtitle.empty"
    )
    assert vm.case_title_model(vm.problematic_cases[0]) == EvaluationText(
        "tests.case.empty.title"
    )


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
            "CASE 1\nINSTRUMENT: BIG_FIVE_SHORT\n"
            "TRAIT: Extraversion\nKEY: E1\nREVERSE: 0\n"
            "ITEM: Я легко начинаю диалог первым.\n"
            "PROMPT: Насколько это похоже?\n\nШкала 1-5\n"
            "STATUS: Модель отвечает\nVALID_SCORE: 1\n"
            "RAW_RESPONSE: SCORE: 4\nRESPONSE: SCORE: 4\n\n"
            "CASE 2\nINSTRUMENT: BIG_FIVE_SHORT\n"
            "TRAIT: Agreeableness\nKEY: A1\nREVERSE: 0\n"
            "ITEM: Я учитываю состояние собеседника.\n"
            "STATUS: Модель отвечает\nVALID_SCORE: 1\n"
            "RAW_RESPONSE: SCORE: 5\nRESPONSE: SCORE: 5",
            "Портрет собран",
            "2026-04-26T16:00:00Z",
        ),
    )
    connection.commit()

    service = _build_service(connection)
    rows = service.list_experiments()
    assert len(rows) == 1
    assert rows[0].status == "Портрет собран"
    assert rows[0].status_code is EvaluationRunStatus.COMPLETED

    vm = TestsViewModel(experiments_service=service)

    _assert_base_projection(vm)
    assert vm.header_title_model() == EvaluationText(
        "tests.header.title.run",
        {"title": "Big Five portrait · 2026-04-26 16:00"},
    )
    assert vm.header_subtitle_model() == EvaluationText(
        "tests.header.subtitle.summary",
        {"passed": 10, "total": 10, "model_version": "—"},
    )
    assert len(vm.problematic_cases) == 2
    case = vm.problematic_cases[0]
    assert vm.case_title_model(case) == EvaluationText(
        "tests.case.title",
        {"index": 1},
    )
    note_models = vm.case_note_models(case)
    assert any(
        isinstance(item, EvaluationText)
        and item.key == "tests.case.field.status"
        for item in note_models
    )
    assert EvaluationText(
        "tests.case.field.trait",
        {"value": "Extraversion"},
    ) in note_models
    assert EvaluationText(
        "tests.case.field.item",
        {"value": "Я легко начинаю диалог первым."},
    ) in note_models
    assert EvaluationText(
        "tests.case.field.response",
        {"value": "SCORE: 4"},
    ) in note_models


def test_tests_viewmodel_run_result_uses_machine_semantics_only() -> None:
    vm = TestsViewModel()

    vm.finish_run(
        ExperimentRunResult(
            ok=False,
            message="This human-readable message must never be presented",
            message_code="resource_busy",
        )
    )

    assert vm.header_subtitle_model() == EvaluationText(
        "tests.message.resource_busy"
    )
    _assert_base_projection(vm)
    assert "human-readable" not in vm.subtitle

    vm.finish_run(
        ExperimentRunResult(
            ok=False,
            message="Legacy visible fallback",
            message_code="Legacy visible fallback",
        )
    )

    assert vm.header_subtitle_model() == EvaluationText(
        "tests.message.result_unavailable"
    )
    _assert_base_projection(vm)
    assert "Legacy visible fallback" not in vm.subtitle

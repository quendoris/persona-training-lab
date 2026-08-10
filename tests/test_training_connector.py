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
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.viewmodels.training import (
    TrainingText,
    TrainingViewModel,
)


def _build_service(connection: sqlite3.Connection) -> TrainingService:
    repo = SQLiteTrainingRepository(connection)
    return TrainingService(training_repo=repo)


def _render_base(value: str | TrainingText) -> str:
    if isinstance(value, str):
        return value
    rendered_values = {
        key: _render_base(item) if isinstance(item, TrainingText) else item
        for key, item in value.values.items()
    }
    return localized_text(None, value.key, **rendered_values)


def _assert_semantic_compatibility(vm: TrainingViewModel) -> None:
    assert vm.title == _render_base(vm.header_title_model())
    assert vm.subtitle == _render_base(vm.header_subtitle_model())
    assert vm.progress_note == _render_base(vm.progress_model())
    assert vm.logs == tuple(_render_base(item) for item in vm.log_models())
    assert vm.risk_title == _render_base(vm.risk_title_model())
    assert vm.risk_body == _render_base(vm.risk_body_model())
    assert vm.next_step == _render_base(vm.next_step_model())
    assert vm.local_model_status == _render_base(vm.local_model_status_model())
    assert vm.local_model_note == _render_base(vm.local_model_note_model())

    selected_models = vm.selected_object_models(vm.selected_objects)
    assert vm.selected_objects == tuple(
        (_render_base(label), value)
        for label, value in selected_models
    )
    assert vm.monitor_rows == tuple(
        (_render_base(label), value, _render_base(note))
        for label, value, note in vm.monitor_models()
    )

    for metric in vm.stat_cards:
        assert metric.title == _render_base(vm.metric_title_model(metric))
        assert metric.note == _render_base(vm.metric_note_model(metric))
    for checkpoint in vm.checkpoints:
        assert checkpoint.name == _render_base(
            vm.checkpoint_name_model(checkpoint)
        )
        assert checkpoint.note == _render_base(
            vm.checkpoint_note_model(checkpoint)
        )
    for version in vm.personality_versions:
        assert version.title == _render_base(vm.version_title_model(version))
        assert version.status == _render_base(vm.version_status_model(version))
        assert version.note == _render_base(vm.version_note_model(version))

    versions_status = vm.versions_status_model()
    assert vm.versions_status_message == (
        _render_base(versions_status) if versions_status is not None else ""
    )


def test_training_connector_empty_state_is_semantic() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    rows = service.list_training_runs()
    assert rows == []

    vm = TrainingViewModel(training_service=service)
    assert vm.status_code == "idle"
    assert isinstance(vm.header_title_model(), TrainingText)
    assert vm.header_title_model().key == "training.header.title"
    assert isinstance(vm.status_model(), TrainingText)
    assert vm.status_model().key == "training.status.idle"
    _assert_semantic_compatibility(vm)


def test_training_connector_single_row_preserves_data_and_semantic_copy() -> None:
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
    assert vm.status == "выполняется · checkpoint-safe"
    assert vm.status_code == TrainingRunStatus.RUNNING.value
    assert vm.training_in_progress is True
    assert vm.can_start_run is False
    assert vm.selected_objects[0][1] == "Qwen 2B"
    assert vm.stat_cards[0].value == "3 / 8"
    assert isinstance(vm.status_model(), TrainingText)
    assert vm.status_model().key == "training.status.running"
    assert all(
        isinstance(item, TrainingText)
        for item in vm.log_models()
    )

    assert vm.title == _render_base(vm.header_title_model())
    assert vm.subtitle == _render_base(vm.header_subtitle_model())
    assert vm.progress_note == _render_base(vm.progress_model())
    assert vm.logs == tuple(_render_base(item) for item in vm.log_models())
    assert vm.risk_title == _render_base(vm.risk_title_model())
    assert vm.risk_body == _render_base(vm.risk_body_model())
    assert vm.next_step == _render_base(vm.next_step_model())
    assert vm.selected_objects == tuple(
        (_render_base(label), value)
        for label, value in vm.selected_object_models(vm.selected_objects)
    )
    for metric in vm.stat_cards:
        assert metric.title == _render_base(vm.metric_title_model(metric))
        assert metric.note == _render_base(vm.metric_note_model(metric))
    for checkpoint in vm.checkpoints:
        assert checkpoint.name == _render_base(
            vm.checkpoint_name_model(checkpoint)
        )
        assert checkpoint.note == _render_base(
            vm.checkpoint_note_model(checkpoint)
        )


def test_unknown_legacy_worker_message_never_becomes_presentation() -> None:
    vm = TrainingViewModel()
    human_message = "A producer supplied a human-readable failure"

    vm.finish_training_run(False, human_message)

    assert vm.creation_message == human_message
    model = vm.current_message()
    assert isinstance(model, TrainingText)
    assert model.key == "training.message.result_unavailable"
    assert human_message not in _render_base(model)


def test_local_inference_internal_failures_use_machine_status_codes() -> None:
    vm = TrainingViewModel()

    status, response = vm.run_local_inference_sync("probe")
    vm.finish_local_inference(status, response)

    assert status == "inference_unavailable"
    assert response == ""
    assert vm.local_inference_status_code.value == "inference_unavailable"
    model = vm.local_inference_status_model()
    assert isinstance(model, TrainingText)
    assert model.key == "training.local_model.status.inference_unavailable"

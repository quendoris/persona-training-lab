from __future__ import annotations

import sqlite3

import pytest

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    ModelProbeResult,
)
from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.application.training.service import (
    TrainingConfigurationError,
    TrainingService,
    TrainingValidationError,
)
from persona_training_lab.domain.training.statuses import TrainingRunStatus
from persona_training_lab.infrastructure.persistence.repositories.datasets import (
    SQLiteDatasetsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.profiles import (
    SQLiteProfilesRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.training import (
    SQLiteTrainingRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema


class _ReadyProbe:
    def check_model_files(self, model_path: str) -> ModelProbeResult:
        return ModelProbeResult(status="Модель найдена", details=f"ok: {model_path}")

    def check_inference_backend(self, model_path: str) -> InferenceProbeResult:
        return InferenceProbeResult(message="Inference backend пока не подключён")


class _MissingModelProbe:
    def check_model_files(self, model_path: str) -> ModelProbeResult:
        return ModelProbeResult(status="Модель не найдена", details=f"missing: {model_path}")

    def check_inference_backend(self, model_path: str) -> InferenceProbeResult:
        return InferenceProbeResult(message="Inference backend пока не подключён")


def _seed_profile(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO persona_profiles (id, title, subtitle, status, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("prf_001", "Mia core v3", "core persona", "готов", "2026-04-27T00:00:00Z"),
    )


def _seed_second_profile(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO persona_profiles (id, title, subtitle, status, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("prf_002", "Mia refined v4", "refined persona", "готов", "2026-04-27T00:00:01Z"),
    )


def _seed_dataset(connection: sqlite3.Connection, *, status: str) -> None:
    is_approved = status == "Одобрен для обучения"
    is_ready = status in {"Готов к обучению", "Одобрен для обучения"}
    connection.execute(
        """
        INSERT INTO datasets (
            id, title, subtitle, path, format, status, record_count,
            valid_count, invalid_count, linked_profile, quality_summary,
            validation_errors_preview, readiness, schema_name, content_sha256,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "ds_001",
            "curated_rose_v07",
            "dataset",
            "/tmp/curated_rose_v07.jsonl",
            "jsonl",
            status,
            100,
            100 if is_ready else 90,
            0 if is_ready else 10,
            "—",
            "summary",
            "",
            "Одобрен для обучения" if is_approved else status,
            "jsonl_finetune_v1",
            "approved-sha" if is_approved else "",
            "2026-04-27T00:00:00Z",
            "2026-04-27T00:00:00Z",
        ),
    )


def _build_service(connection: sqlite3.Connection, probe: object) -> TrainingService:
    return TrainingService(
        training_repo=SQLiteTrainingRepository(connection),
        profiles_service=ProfilesService(
            profiles_repo=SQLiteProfilesRepository(connection)
        ),
        datasets_service=DatasetsService(
            datasets_repo=SQLiteDatasetsRepository(connection)
        ),
        local_model_service=LocalModelService(probe_provider=probe),
    )


def test_successful_create_training_run() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    _seed_profile(connection)
    _seed_dataset(connection, status="Одобрен для обучения")
    connection.commit()

    service = _build_service(connection, _ReadyProbe())

    created = service.create_training_run(
        title="Run A",
        profile_id="prf_001",
        dataset_id="ds_001",
        base_model="Qwen3.5-0.8B",
        epochs=3,
        batch_size=8,
        learning_rate=0.0002,
    )

    assert created.status == TrainingRunStatus.READY.value
    assert created.status_code is TrainingRunStatus.READY
    assert created.profile_id == "prf_001"
    assert created.dataset_id == "ds_001"
    assert created.epochs == 3
    assert created.batch_size == 8
    assert created.learning_rate == pytest.approx(0.0002)
    runs = service.list_training_runs()
    assert len(runs) == 1
    assert runs[0].title == "Run A"
    assert runs[0].profile_id == "prf_001"
    assert runs[0].dataset_id == "ds_001"
    assert runs[0].epochs == 3
    assert runs[0].batch_size == 8
    assert runs[0].learning_rate == pytest.approx(0.0002)


def test_dataset_not_ready_configuration_error() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    _seed_profile(connection)
    _seed_dataset(connection, status="Готов к обучению")
    connection.commit()

    service = _build_service(connection, _ReadyProbe())

    with pytest.raises(TrainingConfigurationError) as captured:
        service.create_training_run(
            title="Run B",
            profile_id="prf_001",
            dataset_id="ds_001",
            base_model="Qwen3.5-0.8B",
            epochs=3,
            batch_size=8,
            learning_rate=0.0002,
        )
    assert captured.value.code == "dataset_required"


def test_missing_model_configuration_error() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    _seed_profile(connection)
    _seed_dataset(connection, status="Одобрен для обучения")
    connection.commit()

    service = _build_service(connection, _MissingModelProbe())

    with pytest.raises(TrainingConfigurationError) as captured:
        service.create_training_run(
            title="Run C",
            profile_id="prf_001",
            dataset_id="ds_001",
            base_model="Qwen3.5-0.8B",
            epochs=3,
            batch_size=8,
            learning_rate=0.0002,
        )
    assert captured.value.code == "model_required"


def test_invalid_hyperparameters_validation_error() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    _seed_profile(connection)
    _seed_dataset(connection, status="Одобрен для обучения")
    connection.commit()

    service = _build_service(connection, _ReadyProbe())

    with pytest.raises(TrainingValidationError) as captured:
        service.create_training_run(
            title="Run D",
            profile_id="prf_001",
            dataset_id="ds_001",
            base_model="Qwen3.5-0.8B",
            epochs=0,
            batch_size=8,
            learning_rate=0.0002,
        )
    assert captured.value.code == "invalid_hyperparameters"


def test_repository_persists_created_training_run() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    repo = SQLiteTrainingRepository(connection)
    repo.create_training_run(
        {
            "id": "trn_persist_1",
            "title": "Persist test",
            "subtitle": "Persist subtitle",
            "status": "ready",
            "base_model": "Qwen",
            "profile": "Mia",
            "dataset_version": "ds",
            "profile_id": "prf_001",
            "dataset_id": "ds_001",
            "mode": "Full fine-tune",
            "epochs": "2",
            "batch_size": "4",
            "learning_rate": "0.0003",
            "epoch_progress": "0 / 2",
            "loss": "—",
            "speed": "—",
            "checkpoints_count": "00",
            "updated_at": "2026-04-27T00:00:00Z",
        }
    )

    rows = repo.list_training_runs()
    assert len(rows) == 1
    assert rows[0]["run_id"] == "trn_persist_1"
    assert rows[0]["profile_id"] == "prf_001"
    assert rows[0]["dataset_id"] == "ds_001"
    assert rows[0]["epochs"] == "2"
    assert rows[0]["batch_size"] == "4"


def test_create_training_run_uses_selected_profile_id() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    _seed_profile(connection)
    _seed_second_profile(connection)
    _seed_dataset(connection, status="Одобрен для обучения")
    connection.commit()

    service = _build_service(connection, _ReadyProbe())
    created = service.create_training_run(
        title="Run E",
        profile_id="prf_002",
        dataset_id="ds_001",
        base_model="Qwen3.5-0.8B",
        epochs=2,
        batch_size=4,
        learning_rate=0.0003,
    )

    assert created.profile == "Mia refined v4"
    assert created.profile_id == "prf_002"
    runs = service.list_training_runs()
    assert runs[0].profile == "Mia refined v4"
    assert runs[0].profile_id == "prf_002"

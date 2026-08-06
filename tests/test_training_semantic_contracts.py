from __future__ import annotations

import pytest

from persona_training_lab.application.datasets.service import DatasetSummary
from persona_training_lab.application.local_model.service import (
    LocalModelService,
)
from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    ModelProbeResult,
)
from persona_training_lab.application.profiles.service import ProfileSummary
from persona_training_lab.application.training.service import (
    TrainingService,
    TrainingValidationError,
)
from persona_training_lab.domain.training.statuses import TrainingRunStatus


class MemoryTrainingRepository:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None

    def list_training_runs(self) -> list[dict[str, object]]:
        return []

    def create_training_run(self, payload: dict[str, object]) -> None:
        self.created = payload


class ProfilesSource:
    def list_profiles(self) -> list[ProfileSummary]:
        return [
            ProfileSummary(
                profile_id="profile",
                title="Mia core",
                subtitle="core",
                description="core",
                communication_style="direct",
                principles="honesty",
                constraints="continuity",
                notes="",
                status="ready",
            )
        ]


class DatasetsSource:
    def list_datasets(self) -> list[DatasetSummary]:
        return [
            DatasetSummary(
                dataset_id="dataset",
                title="curated_v1",
                subtitle="dataset",
                status="approved for training",
                record_count=10,
                valid_count=10,
                invalid_count=0,
                quality_summary="ok",
                validation_errors_preview="",
                path="dataset.jsonl",
                format="jsonl",
            )
        ]


class EnglishReadyProbe:
    def check_model_files(self, model_path: str) -> ModelProbeResult:
        return ModelProbeResult(
            status="Model found",
            details=f"ok: {model_path}",
        )

    def check_inference_backend(
        self,
        _model_path: str,
    ) -> InferenceProbeResult:
        return InferenceProbeResult(message="not used")


def test_training_creation_accepts_semantic_english_dependency_states() -> None:
    repository = MemoryTrainingRepository()
    service = TrainingService(
        training_repo=repository,
        profiles_service=ProfilesSource(),
        datasets_service=DatasetsSource(),
        local_model_service=LocalModelService(
            probe_provider=EnglishReadyProbe()
        ),
    )

    created = service.create_training_run(
        title="Run",
        profile_id="profile",
        dataset_id="dataset",
        base_model="Qwen",
        epochs=2,
        batch_size=4,
        learning_rate=0.0002,
    )

    assert created.status_code is TrainingRunStatus.READY
    assert created.status == "Готов к запуску"
    assert repository.created is not None
    assert repository.created["status"] == "Готов к запуску"


def test_training_validation_error_exposes_stable_code() -> None:
    service = TrainingService(training_repo=MemoryTrainingRepository())

    with pytest.raises(TrainingValidationError) as captured:
        service.create_training_run(
            title="Run",
            profile_id="profile",
            dataset_id="dataset",
            base_model="Qwen",
            epochs=0,
            batch_size=4,
            learning_rate=0.0002,
        )

    assert captured.value.code == "invalid_hyperparameters"
    assert "гиперпараметры" in str(captured.value)

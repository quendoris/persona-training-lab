from __future__ import annotations

import sqlite3
from pathlib import Path

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    ModelProbeResult,
)
from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.application.training.full_backend import FullFineTuneResult
from persona_training_lab.application.training.input_pipeline import TrainingSample
from persona_training_lab.application.training.service import TrainingService
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
        return ModelProbeResult(status="Модель найдена", details=model_path)

    def check_inference_backend(self, model_path: str) -> InferenceProbeResult:
        return InferenceProbeResult(message=model_path)


class _BackendSpy:
    def __init__(self) -> None:
        self.calls = 0
        self.provenance: dict[str, object] = {}

    def run(
        self,
        run_id: str,
        model_path: str,
        samples: tuple[TrainingSample, ...],
        *,
        epochs: int = 1,
        batch_size: int = 1,
        learning_rate: float = 1e-4,
        provenance: dict[str, object] | None = None,
    ) -> FullFineTuneResult:
        self.calls += 1
        self.provenance = dict(provenance or {})
        return FullFineTuneResult(
            status=TrainingRunStatus.COMPLETED.value,
            message="full_finetune_completed",
            artifact_path=f"artifacts/full_finetune/{run_id}/model",
            epochs=epochs,
            max_steps=max(1, epochs),
            learning_rate=learning_rate,
            trainable_params=1,
            initial_loss=1.0,
            final_loss=0.5,
        )


def _build_service(
    connection: sqlite3.Connection,
    tmp_path: Path,
) -> tuple[TrainingService, str, Path, _BackendSpy]:
    profile_repo = SQLiteProfilesRepository(connection)
    profiles = ProfilesService(profiles_repo=profile_repo)
    result, profile = profiles.create_profile(
        title="Mia",
        description="Calm and precise.",
        communication_style="Direct but kind.",
        principles="State uncertainty.",
        constraints="Do not invent facts.",
        notes="operator note",
    )
    assert result.ok and profile is not None

    dataset_path = tmp_path / "training.jsonl"
    dataset_path.write_text(
        '{"prompt":"Hello","response":"Hi."}\n',
        encoding="utf-8",
    )
    datasets = DatasetsService(
        datasets_repo=SQLiteDatasetsRepository(connection)
    )
    dataset = datasets.add_dataset_from_path(str(dataset_path))
    assert datasets.approve_dataset(dataset.dataset_id).ok

    backend = _BackendSpy()
    service = TrainingService(
        training_repo=SQLiteTrainingRepository(connection),
        profiles_service=profiles,
        datasets_service=datasets,
        local_model_service=LocalModelService(probe_provider=_ReadyProbe()),
        full_backend=backend,
    )
    run = service.create_training_run(
        title="Pinned inputs",
        profile_id=profile.profile_id,
        dataset_id=dataset.dataset_id,
        base_model=str(tmp_path / "model"),
        epochs=1,
        batch_size=1,
        learning_rate=0.0001,
    )
    return service, run.run_id, dataset_path, backend


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    return connection


def test_run_persists_profile_and_dataset_fingerprints(tmp_path: Path) -> None:
    connection = _connection()
    service, run_id, _dataset_path, _backend = _build_service(connection, tmp_path)

    run = next(item for item in service.list_training_runs() if item.run_id == run_id)

    assert len(run.profile_sha256) == 64
    assert len(run.dataset_sha256) == 64
    assert run.profile_sha256 != run.dataset_sha256


def test_profile_change_after_run_creation_blocks_training(tmp_path: Path) -> None:
    connection = _connection()
    service, run_id, _dataset_path, backend = _build_service(connection, tmp_path)
    run = service.list_training_runs()[0]
    assert service.profiles_service is not None

    updated = service.profiles_service.update_profile(
        profile_id=run.profile_id,
        title="Mia",
        description="Changed persona description.",
        communication_style="Direct but kind.",
        principles="State uncertainty.",
        constraints="Do not invent facts.",
        notes="operator note",
    )
    assert updated.ok

    result = service.start_full_finetune_run(run_id)

    assert not result.ok
    assert backend.calls == 0
    persisted = service.list_training_runs()[0]
    assert persisted.status_code is TrainingRunStatus.FAILED
    assert persisted.error_message == "profile_changed_after_run_creation"


def test_operator_notes_change_does_not_invalidate_run(tmp_path: Path) -> None:
    connection = _connection()
    service, run_id, _dataset_path, backend = _build_service(connection, tmp_path)
    run = service.list_training_runs()[0]
    assert service.profiles_service is not None

    profile = next(
        item
        for item in service.profiles_service.list_profiles()
        if item.profile_id == run.profile_id
    )
    updated = service.profiles_service.update_profile(
        profile_id=profile.profile_id,
        title=profile.title,
        description=profile.description,
        communication_style=profile.communication_style,
        principles=profile.principles,
        constraints=profile.constraints,
        notes="new operator-only note",
    )
    assert updated.ok

    result = service.start_full_finetune_run(run_id)

    assert result.ok
    assert backend.calls == 1
    assert "operator-only" not in str(backend.provenance.get("profile_instruction", ""))


def test_dataset_reapproval_after_run_creation_blocks_training(tmp_path: Path) -> None:
    connection = _connection()
    service, run_id, dataset_path, backend = _build_service(connection, tmp_path)
    run = service.list_training_runs()[0]
    assert service.datasets_service is not None

    dataset_path.write_text(
        '{"prompt":"Changed","response":"New approved bytes."}\n',
        encoding="utf-8",
    )
    assert service.datasets_service.approve_dataset(run.dataset_id).ok

    result = service.start_full_finetune_run(run_id)

    assert not result.ok
    assert backend.calls == 0
    persisted = service.list_training_runs()[0]
    assert persisted.status_code is TrainingRunStatus.FAILED
    assert persisted.error_message == "dataset_changed_after_run_creation"


def test_successful_launch_records_exact_input_provenance(tmp_path: Path) -> None:
    connection = _connection()
    service, run_id, _dataset_path, backend = _build_service(connection, tmp_path)
    run = service.list_training_runs()[0]

    result = service.start_full_finetune_run(run_id)

    assert result.ok
    assert backend.calls == 1
    assert backend.provenance["profile_sha256"] == run.profile_sha256
    assert backend.provenance["dataset_sha256"] == run.dataset_sha256
    assert backend.provenance["run_dataset_sha256"] == run.dataset_sha256
    assert "Persona: Mia" in str(backend.provenance["profile_instruction"])

from __future__ import annotations

import sqlite3
from pathlib import Path

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.model_versions.quality import parse_model_version_quality
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.ports.local_model_probe import (
    InferenceProbeResult,
    ModelProbeResult,
)
from persona_training_lab.application.profiles.service import ProfilesService
from persona_training_lab.application.training.full_backend import FullFineTuneResult
from persona_training_lab.application.training.input_pipeline import TrainingSample
from persona_training_lab.application.training.service import (
    TrainingService,
    TrainingValidationError,
)
from persona_training_lab.domain.models.statuses import ModelVersionStatus
from persona_training_lab.domain.training.statuses import TrainingRunStatus
from persona_training_lab.infrastructure.persistence.repositories.datasets import (
    SQLiteDatasetsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.model_versions import (
    SQLiteModelVersionsRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.profiles import (
    SQLiteProfilesRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.training import (
    SQLiteTrainingRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema
from persona_training_lab.ui.viewmodels.training import TrainingText, TrainingViewModel


class _ReadyProbe:
    def check_model_files(self, model_path: str) -> ModelProbeResult:
        return ModelProbeResult(status="Модель найдена", details=model_path)

    def check_inference_backend(self, model_path: str) -> InferenceProbeResult:
        return InferenceProbeResult(message=model_path)


class _FullBackend:
    def __init__(self) -> None:
        self.samples: tuple[TrainingSample, ...] = ()
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
        self.samples = tuple(samples)
        self.provenance = dict(provenance or {})
        return FullFineTuneResult(
            status=TrainingRunStatus.COMPLETED.value,
            message="full_finetune_completed",
            artifact_path=f"artifacts/full_finetune/{run_id}/model",
            epochs=epochs,
            max_steps=max(1, epochs),
            learning_rate=learning_rate,
            trainable_params=42,
            initial_loss=1.0,
            final_loss=0.1,
        )


def _seed_profile(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO persona_profiles (
            id, title, subtitle, description, communication_style,
            principles, constraints, notes, status, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "prf_run",
            "Mia",
            "persona",
            "Calm and precise.",
            "Direct but kind.",
            "State uncertainty.",
            "Do not invent facts.",
            "operator note",
            "ready",
            "2026-01-01T00:00:00+00:00",
        ),
    )
    connection.commit()


def _configured_service(
    connection: sqlite3.Connection,
    tmp_path: Path,
    *,
    backend: _FullBackend | None = None,
) -> tuple[TrainingService, str, _FullBackend]:
    _seed_profile(connection)
    dataset_path = tmp_path / "training.jsonl"
    dataset_path.write_text(
        '{"prompt":"Say hello","response":"Hello."}\n'
        '{"instruction":"Answer honestly","input":"Unsure?","output":"I am uncertain."}\n',
        encoding="utf-8",
    )
    datasets_service = DatasetsService(
        datasets_repo=SQLiteDatasetsRepository(connection)
    )
    dataset = datasets_service.add_dataset_from_path(str(dataset_path))
    approved = datasets_service.approve_dataset(dataset.dataset_id)
    assert approved.ok

    selected_backend = backend or _FullBackend()
    service = TrainingService(
        training_repo=SQLiteTrainingRepository(connection),
        profiles_service=ProfilesService(
            profiles_repo=SQLiteProfilesRepository(connection)
        ),
        datasets_service=datasets_service,
        local_model_service=LocalModelService(probe_provider=_ReadyProbe()),
        full_backend=selected_backend,
    )
    run = service.create_training_run(
        title="Run",
        profile_id="prf_run",
        dataset_id=dataset.dataset_id,
        base_model=str(tmp_path / "model"),
        epochs=3,
        batch_size=1,
        learning_rate=0.0001,
    )
    return service, run.run_id, selected_backend


def test_start_and_complete_training_run(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    service, run_id, backend = _configured_service(conn, tmp_path)

    result = service.start_full_finetune_run(run_id)

    assert result.ok is True
    assert result.code == "completed"
    assert result.values["artifact"] == f"artifacts/full_finetune/{run_id}/model"
    assert [sample.response for sample in backend.samples] == [
        "Hello.",
        "I am uncertain.",
    ]
    assert backend.provenance["profile_id"] == "prf_run"
    assert backend.provenance["sample_count"] == 2
    assert backend.provenance["dataset_sha256"]
    row = service.list_training_runs()[0]
    assert row.status_code is TrainingRunStatus.COMPLETED
    assert row.artifact_path == f"artifacts/full_finetune/{run_id}/model"
    logs = service.list_training_run_logs(run_id)
    assert any("full_finetune_started" in log for log in logs)
    assert any("artifact_saved:" in log for log in logs)


def test_dataset_change_after_approval_blocks_training(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    service, run_id, backend = _configured_service(conn, tmp_path)

    dataset_path = tmp_path / "training.jsonl"
    dataset_path.write_text(
        '{"prompt":"Changed","response":"Different bytes."}\n',
        encoding="utf-8",
    )

    result = service.start_full_finetune_run(run_id)

    assert not result.ok
    assert result.code == "start_failed"
    assert backend.samples == ()
    row = service.list_training_runs()[0]
    assert row.status_code is TrainingRunStatus.FAILED
    assert row.error_message == "dataset_changed_after_approval"


def test_start_missing_run_fails(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    service, _run_id, _backend = _configured_service(conn, tmp_path)

    try:
        service.start_training_run("missing")
    except TrainingValidationError as exc:
        assert exc.code == "run_not_found"
    else:
        raise AssertionError("expected TrainingValidationError")


def test_cannot_start_non_ready_run(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    service, run_id, _backend = _configured_service(conn, tmp_path)
    conn.execute(
        "UPDATE training_runs SET status = ? WHERE id = ?",
        (TrainingRunStatus.COMPLETED.value, run_id),
    )
    conn.commit()

    try:
        service.start_training_run(run_id)
    except TrainingValidationError as exc:
        assert exc.code == "not_ready"
    else:
        raise AssertionError("expected TrainingValidationError")


def test_viewmodel_start_action(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    service, run_id, _backend = _configured_service(conn, tmp_path)
    vm = TrainingViewModel(training_service=service)

    ok, code = vm.start_selected_training_run()

    assert ok
    assert code == "completed"
    assert vm.creation_message == "completed"
    message_model = vm.current_message()
    assert message_model is not None
    assert message_model.key == "training.message.completed"
    assert message_model.values["artifact"] == f"artifacts/full_finetune/{run_id}/model"
    assert vm.status_code == TrainingRunStatus.COMPLETED.value
    assert vm.status_model().key == "training.status.completed"


def test_viewmodel_publishes_machine_model_version_quality(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_minimal_schema(conn)
    service, run_id, _backend = _configured_service(conn, tmp_path)
    model_versions_service = ModelVersionsService(
        model_versions_repo=SQLiteModelVersionsRepository(conn)
    )
    vm = TrainingViewModel(
        training_service=service,
        model_versions_service=model_versions_service,
    )

    ok, code = vm.start_selected_training_run()

    assert ok
    assert code == "completed"
    row = conn.execute(
        """
        SELECT status, quality_summary
        FROM model_versions
        WHERE training_run_id = ?
        """,
        (run_id,),
    ).fetchone()
    assert row is not None
    assert row["status"] == ModelVersionStatus.READY.value
    assert row["quality_summary"].startswith("ptl:model-version-quality:v1:")
    quality = parse_model_version_quality(row["quality_summary"])
    assert quality is not None
    assert quality.code == "training_completed"
    assert dict(quality.values) == {
        "checkpoints": "01",
        "loss": "0.100000",
    }

    version = vm.personality_versions[0]
    assert version.status_code == ModelVersionStatus.READY.value
    note_model = vm.version_note_model(version)
    assert isinstance(note_model, TrainingText)
    assert note_model.key == "training.version.note"

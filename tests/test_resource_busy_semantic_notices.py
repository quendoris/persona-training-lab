from __future__ import annotations

from persona_training_lab.application.datasets.service import DatasetSummary
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.application.ports.local_model_probe import ModelProbeResult
from persona_training_lab.application.profiles.service import ProfileSummary
from persona_training_lab.application.runtime.operations import (
    OperationBlocker,
    OperationConflictError,
    ResourceClaim,
    RuntimeOperation,
)
from persona_training_lab.application.training.input_pipeline import (
    profile_training_sha256,
)
from persona_training_lab.application.training.service import TrainingService
from persona_training_lab.domain.training.statuses import TrainingRunStatus


class _RecordingReporter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def report_message(self, message: str, **kwargs: object) -> str:
        self.calls.append((message, dict(kwargs)))
        return "corr_test"


class _ExperimentsRepository:
    def list_experiments(self) -> list[dict[str, str]]:
        return []


class _LocalModel:
    model_path = "/models/base"

    @staticmethod
    def resolve_model_path(reference: str) -> str:
        return reference or _LocalModel.model_path

    @staticmethod
    def probe_model_files_at(_model_path: str) -> ModelProbeResult:
        return ModelProbeResult(status="found")


class _Profiles:
    def __init__(self, profile: ProfileSummary) -> None:
        self.profile = profile

    def list_profiles(self) -> list[ProfileSummary]:
        return [self.profile]


class _Datasets:
    def __init__(self, dataset: DatasetSummary) -> None:
        self.dataset = dataset

    def list_datasets(self) -> list[DatasetSummary]:
        return [self.dataset]


class _TrainingRepository:
    def __init__(self, run: dict[str, str]) -> None:
        self.run = run
        self.logs: list[tuple[str, str, str]] = []

    def get_training_run(self, run_id: str) -> dict[str, str] | None:
        return self.run if run_id == self.run["run_id"] else None

    def add_training_log(self, run_id: str, level: str, message: str) -> None:
        self.logs.append((run_id, level, message))


def _conflict() -> OperationConflictError:
    operation = RuntimeOperation(
        operation_id="op_blocker",
        operation_kind="personality_test",
        subject_kind="experiment",
        subject_id="evr_blocker",
        state="running",
        correlation_id="corr_blocker",
        owner_pid=1,
        started_at="2026-09-08T20:00:00Z",
        heartbeat_at="2026-09-08T20:00:00Z",
    )
    return OperationConflictError(
        (
            OperationBlocker(
                operation,
                ResourceClaim("compute_device", "shared", "write"),
            ),
        )
    )


def test_portrait_resource_busy_notice_carries_semantic_user_message(
    monkeypatch,
) -> None:
    reporter = _RecordingReporter()
    service = ExperimentsService(
        experiments_repo=_ExperimentsRepository(),  # type: ignore[arg-type]
        local_model_service=_LocalModel(),  # type: ignore[arg-type]
        error_reporter=reporter,  # type: ignore[arg-type]
    )

    def raise_conflict(*_args, **_kwargs):
        raise _conflict()

    monkeypatch.setattr(
        ExperimentsService,
        "_begin_portrait_operation",
        raise_conflict,
    )

    result = service.run_personality_portrait_test_pack()

    assert result.ok is False
    assert result.message_code == "resource_busy"
    assert len(reporter.calls) == 1
    technical_message, kwargs = reporter.calls[0]
    assert technical_message == "experiments.resource_busy"
    assert kwargs["user_message"] == UserMessage("tests.message.resource_busy")


def test_training_resource_busy_notice_carries_semantic_user_message(
    monkeypatch,
) -> None:
    profile = ProfileSummary(
        profile_id="prf_001",
        title="Mia",
        subtitle="persona",
        description="Calm and precise.",
        communication_style="Direct but kind.",
        principles="State uncertainty.",
        constraints="Do not invent facts.",
        notes="",
        status="ready",
    )
    dataset_hash = "a" * 64
    dataset = DatasetSummary(
        dataset_id="dsv_001",
        title="dataset",
        subtitle="dataset",
        status="approved_for_training",
        record_count=1,
        valid_count=1,
        invalid_count=0,
        quality_summary="ok",
        validation_errors_preview="",
        path="dataset.jsonl",
        format="jsonl",
        content_sha256=dataset_hash,
    )
    run = {
        "run_id": "trn_001",
        "status": TrainingRunStatus.READY.value,
        "base_model": "/models/base",
        "profile_id": profile.profile_id,
        "dataset_id": dataset.dataset_id,
        "profile_sha256": profile_training_sha256(profile),
        "dataset_sha256": dataset_hash,
        "profile": profile.title,
        "dataset_version": dataset.title,
        "epochs": "1",
        "batch_size": "1",
        "learning_rate": "0.0001",
    }
    reporter = _RecordingReporter()
    repository = _TrainingRepository(run)
    service = TrainingService(
        training_repo=repository,  # type: ignore[arg-type]
        profiles_service=_Profiles(profile),  # type: ignore[arg-type]
        datasets_service=_Datasets(dataset),  # type: ignore[arg-type]
        local_model_service=_LocalModel(),  # type: ignore[arg-type]
        full_backend=object(),
        error_reporter=reporter,  # type: ignore[arg-type]
    )

    def raise_conflict(*_args, **_kwargs):
        raise _conflict()

    monkeypatch.setattr(
        TrainingService,
        "_begin_training_operation",
        raise_conflict,
    )

    result = service.start_full_finetune_run("trn_001")

    assert result.ok is False
    assert result.code == "resource_busy"
    assert result.values["blocker_kind"] == "personality_test"
    assert repository.logs[-1] == (
        "trn_001",
        "WARNING",
        "resource_busy:personality_test",
    )
    assert len(reporter.calls) == 1
    technical_message, kwargs = reporter.calls[0]
    assert technical_message == "training.resource_busy"
    assert kwargs["user_message"] == UserMessage("training.message.resource_busy")

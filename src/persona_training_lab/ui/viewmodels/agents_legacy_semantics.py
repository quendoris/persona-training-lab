from __future__ import annotations

from persona_training_lab.application.datasets.status_mapping import (
    normalize_dataset_status,
)
from persona_training_lab.application.experiments.status_mapping import (
    normalize_evaluation_status,
)
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.application.model_versions.status_mapping import (
    normalize_model_version_status,
)
from persona_training_lab.application.training.status_mapping import (
    normalize_training_status,
)
from persona_training_lab.domain.datasets.statuses import DatasetVersionStatus
from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus
from persona_training_lab.domain.models.statuses import ModelVersionStatus
from persona_training_lab.domain.training.statuses import TrainingRunStatus


MISSING = "—"


def messages(*keys: str) -> tuple[UserMessage, ...]:
    return tuple(UserMessage(key) for key in keys)


def dataset_status_message(dataset: object | None) -> UserMessage:
    status = normalize_dataset_status(getattr(dataset, "status", ""))
    key = {
        DatasetVersionStatus.DRAFT: "draft",
        DatasetVersionStatus.IMPORTED: "imported",
        DatasetVersionStatus.VALIDATED: "validated",
        DatasetVersionStatus.APPROVED: "approved",
        DatasetVersionStatus.ARCHIVED: "archived",
        DatasetVersionStatus.UNKNOWN: "unknown",
    }[status]
    return UserMessage(f"agents.legacy.status.dataset.{key}")


def training_status_message(run: object | None) -> UserMessage:
    status = normalize_training_status(getattr(run, "status", ""))
    key = {
        TrainingRunStatus.CREATED: "created",
        TrainingRunStatus.READY: "ready",
        TrainingRunStatus.RUNNING: "running",
        TrainingRunStatus.FAILED: "failed",
        TrainingRunStatus.COMPLETED: "completed",
        TrainingRunStatus.UNKNOWN: "unknown",
    }[status]
    return UserMessage(f"agents.legacy.status.training.{key}")


def version_status_message(version: object | None) -> UserMessage:
    status = normalize_model_version_status(getattr(version, "status", ""))
    key = {
        ModelVersionStatus.DRAFT: "draft",
        ModelVersionStatus.READY: "ready",
        ModelVersionStatus.ARCHIVED: "archived",
        ModelVersionStatus.FAILED: "failed",
        ModelVersionStatus.UNKNOWN: "unknown",
    }[status]
    return UserMessage(f"agents.legacy.status.version.{key}")


def portrait_status_message(experiment: object | None) -> UserMessage:
    status = normalize_evaluation_status(getattr(experiment, "status", ""))
    key = {
        EvaluationRunStatus.CREATED: "created",
        EvaluationRunStatus.RUNNING: "running",
        EvaluationRunStatus.PARTIAL: "partial",
        EvaluationRunStatus.FAILED: "failed",
        EvaluationRunStatus.COMPLETED: "completed",
        EvaluationRunStatus.UNKNOWN: "unknown",
    }[status]
    return UserMessage(f"agents.legacy.status.portrait.{key}")


__all__ = (
    "MISSING",
    "dataset_status_message",
    "messages",
    "portrait_status_message",
    "training_status_message",
    "version_status_message",
)

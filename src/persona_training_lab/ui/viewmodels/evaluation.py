from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)


@dataclass(frozen=True, slots=True)
class EvaluationText:
    key: str
    values: Mapping[str, object] = field(default_factory=dict)


def evaluation_text(key: str, **values: object) -> EvaluationText:
    return EvaluationText(key, MappingProxyType(dict(values)))


_STATUS_KEYS = {
    EvaluationRunStatus.CREATED: "evaluation.status.created",
    EvaluationRunStatus.RUNNING: "evaluation.status.running",
    EvaluationRunStatus.PARTIAL: "evaluation.status.partial",
    EvaluationRunStatus.FAILED: "evaluation.status.failed",
    EvaluationRunStatus.COMPLETED: "evaluation.status.completed",
}


def evaluation_status_text(
    status: EvaluationRunStatus,
    raw_status: str = "",
) -> EvaluationText:
    key = _STATUS_KEYS.get(status)
    if key is not None:
        return evaluation_text(key)
    return evaluation_text(
        "evaluation.status.unknown",
        status=raw_status,
    )

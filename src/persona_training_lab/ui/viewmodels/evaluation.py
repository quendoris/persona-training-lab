from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
)
from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)


@dataclass(frozen=True, slots=True)
class EvaluationText:
    key: str
    values: Mapping[str, object] = field(default_factory=dict)


def evaluation_text(key: str, **values: object) -> EvaluationText:
    return EvaluationText(key, MappingProxyType(dict(values)))


def render_base_evaluation_text(value: str | EvaluationText) -> str:
    """Render the historical base-locale compatibility surface lazily."""

    if isinstance(value, str):
        return value
    from persona_training_lab.ui.i18n.text import text as localized_text

    rendered_values = {
        key: render_base_evaluation_text(item)
        if isinstance(item, EvaluationText)
        else item
        for key, item in value.values.items()
    }
    return localized_text(None, value.key, **rendered_values)


_STATUS_KEYS = {
    EvaluationRunStatus.CREATED: "evaluation.status.created",
    EvaluationRunStatus.RUNNING: "evaluation.status.running",
    EvaluationRunStatus.PARTIAL: "evaluation.status.partial",
    EvaluationRunStatus.FAILED: "evaluation.status.failed",
    EvaluationRunStatus.COMPLETED: "evaluation.status.completed",
}
_LOCAL_MODEL_STATUS_KEYS = {
    LocalModelStatus.UNCHECKED: "tests.model_status.unchecked",
    LocalModelStatus.CHECKING: "tests.model_status.checking",
    LocalModelStatus.FOUND: "tests.model_status.found",
    LocalModelStatus.MISSING: "tests.model_status.missing",
    LocalModelStatus.CHECK_FAILED: "tests.model_status.check_failed",
    LocalModelStatus.NOT_LOADED: "tests.model_status.not_loaded",
    LocalModelStatus.RESPONDING: "tests.model_status.responding",
    LocalModelStatus.INFERENCE_UNAVAILABLE: "tests.model_status.inference_unavailable",
    LocalModelStatus.GENERATING: "tests.model_status.generating",
    LocalModelStatus.EMPTY_RESPONSE: "tests.model_status.empty_response",
    LocalModelStatus.RESOURCE_EXHAUSTED: "tests.model_status.resource_exhausted",
    LocalModelStatus.GENERATION_FAILED: "tests.model_status.generation_failed",
    LocalModelStatus.UNKNOWN: "tests.model_status.unknown",
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


def local_model_status_text(status: LocalModelStatus) -> EvaluationText:
    return evaluation_text(_LOCAL_MODEL_STATUS_KEYS[status])

from __future__ import annotations

from persona_training_lab.domain.evaluation.statuses import EvaluationRunStatus


_STATUS_ALIASES = {
    "создан": EvaluationRunStatus.CREATED,
    "создано": EvaluationRunStatus.CREATED,
    "created": EvaluationRunStatus.CREATED,
    "не запускался": EvaluationRunStatus.CREATED,
    "not started": EvaluationRunStatus.CREATED,
    "выполняется": EvaluationRunStatus.RUNNING,
    "идёт": EvaluationRunStatus.RUNNING,
    "running": EvaluationRunStatus.RUNNING,
    "in progress": EvaluationRunStatus.RUNNING,
    "есть ошибки": EvaluationRunStatus.PARTIAL,
    "частично": EvaluationRunStatus.PARTIAL,
    "partial": EvaluationRunStatus.PARTIAL,
    "completed with errors": EvaluationRunStatus.PARTIAL,
    "ошибка": EvaluationRunStatus.FAILED,
    "сбой": EvaluationRunStatus.FAILED,
    "failed": EvaluationRunStatus.FAILED,
    "error": EvaluationRunStatus.FAILED,
    "портрет собран": EvaluationRunStatus.COMPLETED,
    "пройден": EvaluationRunStatus.COMPLETED,
    "готов": EvaluationRunStatus.COMPLETED,
    "completed": EvaluationRunStatus.COMPLETED,
    "passed": EvaluationRunStatus.COMPLETED,
    "ready": EvaluationRunStatus.COMPLETED,
}


def normalize_evaluation_status(value: object) -> EvaluationRunStatus:
    if isinstance(value, EvaluationRunStatus):
        return value
    normalized = " ".join(str(value or "").strip().casefold().split())
    direct = _STATUS_ALIASES.get(normalized)
    if direct is not None:
        return direct
    for alias, status in _STATUS_ALIASES.items():
        if alias and alias in normalized:
            return status
    return EvaluationRunStatus.UNKNOWN

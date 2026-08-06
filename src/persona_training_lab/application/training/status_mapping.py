from __future__ import annotations

from persona_training_lab.domain.training.statuses import TrainingRunStatus


_EXACT_ALIASES = {
    "created": TrainingRunStatus.CREATED,
    "создан": TrainingRunStatus.CREATED,
    "создано": TrainingRunStatus.CREATED,
    "ready": TrainingRunStatus.READY,
    "ready to start": TrainingRunStatus.READY,
    "готов к запуску": TrainingRunStatus.READY,
    "running": TrainingRunStatus.RUNNING,
    "выполняется": TrainingRunStatus.RUNNING,
    "в процессе": TrainingRunStatus.RUNNING,
    "failed": TrainingRunStatus.FAILED,
    "failure": TrainingRunStatus.FAILED,
    "error": TrainingRunStatus.FAILED,
    "ошибка": TrainingRunStatus.FAILED,
    "completed": TrainingRunStatus.COMPLETED,
    "complete": TrainingRunStatus.COMPLETED,
    "завершено": TrainingRunStatus.COMPLETED,
    "завершён": TrainingRunStatus.COMPLETED,
    "завершен": TrainingRunStatus.COMPLETED,
}
_PREFIX_ALIASES = (
    ("выполняется", TrainingRunStatus.RUNNING),
    ("running", TrainingRunStatus.RUNNING),
    ("готов к запуску", TrainingRunStatus.READY),
    ("ready", TrainingRunStatus.READY),
    ("заверш", TrainingRunStatus.COMPLETED),
    ("complet", TrainingRunStatus.COMPLETED),
    ("ошибка", TrainingRunStatus.FAILED),
    ("failed", TrainingRunStatus.FAILED),
    ("error", TrainingRunStatus.FAILED),
)


def normalize_training_status(value: object) -> TrainingRunStatus:
    normalized = " ".join(str(value or "").strip().casefold().split())
    exact = _EXACT_ALIASES.get(normalized)
    if exact is not None:
        return exact
    for prefix, status in _PREFIX_ALIASES:
        if normalized.startswith(prefix):
            return status
    return TrainingRunStatus.UNKNOWN

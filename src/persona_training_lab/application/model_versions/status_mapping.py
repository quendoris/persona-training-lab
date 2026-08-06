from __future__ import annotations

from persona_training_lab.domain.models.statuses import ModelVersionStatus


_STATUS_ALIASES = {
    "": ModelVersionStatus.UNKNOWN,
    "unknown": ModelVersionStatus.UNKNOWN,
    "неизвестно": ModelVersionStatus.UNKNOWN,
    "draft": ModelVersionStatus.DRAFT,
    "черновик": ModelVersionStatus.DRAFT,
    "ready": ModelVersionStatus.READY,
    "available": ModelVersionStatus.READY,
    "stable": ModelVersionStatus.READY,
    "готов": ModelVersionStatus.READY,
    "готова": ModelVersionStatus.READY,
    "готово": ModelVersionStatus.READY,
    "доступен": ModelVersionStatus.READY,
    "доступна": ModelVersionStatus.READY,
    "archived": ModelVersionStatus.ARCHIVED,
    "archive": ModelVersionStatus.ARCHIVED,
    "архивный": ModelVersionStatus.ARCHIVED,
    "архивная": ModelVersionStatus.ARCHIVED,
    "в архиве": ModelVersionStatus.ARCHIVED,
    "failed": ModelVersionStatus.FAILED,
    "error": ModelVersionStatus.FAILED,
    "ошибка": ModelVersionStatus.FAILED,
    "сбой": ModelVersionStatus.FAILED,
}
_STATUS_SEPARATORS = ("·", "|", ":")


def normalize_model_version_status(value: object) -> ModelVersionStatus:
    if isinstance(value, ModelVersionStatus):
        return value

    normalized = str(value or "").strip().casefold()
    direct = _STATUS_ALIASES.get(normalized)
    if direct is not None:
        return direct

    for separator in _STATUS_SEPARATORS:
        head = normalized.split(separator, 1)[0].strip()
        mapped = _STATUS_ALIASES.get(head)
        if mapped is not None:
            return mapped

    return ModelVersionStatus.UNKNOWN

from __future__ import annotations

from enum import StrEnum


class LocalModelStatus(StrEnum):
    UNCHECKED = "unchecked"
    CHECKING = "checking"
    FOUND = "found"
    MISSING = "missing"
    CHECK_FAILED = "check_failed"
    NOT_LOADED = "not_loaded"
    RESPONDING = "responding"
    INFERENCE_UNAVAILABLE = "inference_unavailable"
    GENERATING = "generating"
    GENERATION_FAILED = "generation_failed"
    UNKNOWN = "unknown"


_STATUS_ALIASES = {
    "модель не проверялась": LocalModelStatus.UNCHECKED,
    "model not checked": LocalModelStatus.UNCHECKED,
    "проверка модели…": LocalModelStatus.CHECKING,
    "проверка модели...": LocalModelStatus.CHECKING,
    "checking model": LocalModelStatus.CHECKING,
    "модель найдена": LocalModelStatus.FOUND,
    "model found": LocalModelStatus.FOUND,
    "модель не найдена": LocalModelStatus.MISSING,
    "model not found": LocalModelStatus.MISSING,
    "не удалось проверить модель": LocalModelStatus.CHECK_FAILED,
    "model check failed": LocalModelStatus.CHECK_FAILED,
    "модель не загружена": LocalModelStatus.NOT_LOADED,
    "model not loaded": LocalModelStatus.NOT_LOADED,
    "модель отвечает": LocalModelStatus.RESPONDING,
    "model responds": LocalModelStatus.RESPONDING,
    "inference backend не подключён": LocalModelStatus.INFERENCE_UNAVAILABLE,
    "inference backend is unavailable": LocalModelStatus.INFERENCE_UNAVAILABLE,
    "генерация…": LocalModelStatus.GENERATING,
    "генерация...": LocalModelStatus.GENERATING,
    "generating": LocalModelStatus.GENERATING,
    "ошибка генерации": LocalModelStatus.GENERATION_FAILED,
    "generation failed": LocalModelStatus.GENERATION_FAILED,
}


def normalize_local_model_status(value: object) -> LocalModelStatus:
    normalized = " ".join(str(value or "").strip().casefold().split())
    return _STATUS_ALIASES.get(normalized, LocalModelStatus.UNKNOWN)

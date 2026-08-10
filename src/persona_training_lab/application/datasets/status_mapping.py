from __future__ import annotations

from persona_training_lab.domain.datasets.statuses import DatasetVersionStatus


_STATUS_ALIASES = {
    "draft": DatasetVersionStatus.DRAFT,
    "черновик": DatasetVersionStatus.DRAFT,
    "imported": DatasetVersionStatus.IMPORTED,
    "импортирован": DatasetVersionStatus.IMPORTED,
    "не проверен": DatasetVersionStatus.IMPORTED,
    "unchecked": DatasetVersionStatus.IMPORTED,
    "validated": DatasetVersionStatus.VALIDATED,
    "готов к обучению": DatasetVersionStatus.VALIDATED,
    "ready for training": DatasetVersionStatus.VALIDATED,
    "approved_for_training": DatasetVersionStatus.APPROVED,
    "approved": DatasetVersionStatus.APPROVED,
    "approved for training": DatasetVersionStatus.APPROVED,
    "одобрен": DatasetVersionStatus.APPROVED,
    "одобрен для обучения": DatasetVersionStatus.APPROVED,
    "structure_error": DatasetVersionStatus.STRUCTURE_ERROR,
    "structure error": DatasetVersionStatus.STRUCTURE_ERROR,
    "ошибка структуры": DatasetVersionStatus.STRUCTURE_ERROR,
    "validation_failed": DatasetVersionStatus.VALIDATION_FAILED,
    "validation failed": DatasetVersionStatus.VALIDATION_FAILED,
    "не удалось проверить датасет": DatasetVersionStatus.VALIDATION_FAILED,
    "archived": DatasetVersionStatus.ARCHIVED,
    "архивный": DatasetVersionStatus.ARCHIVED,
}


def normalize_dataset_status(value: object) -> DatasetVersionStatus:
    normalized = " ".join(str(value or "").strip().casefold().split())
    return _STATUS_ALIASES.get(normalized, DatasetVersionStatus.UNKNOWN)

from enum import StrEnum


class DatasetVersionStatus(StrEnum):
    DRAFT = "draft"
    IMPORTED = "imported"
    VALIDATED = "validated"
    APPROVED = "approved_for_training"
    ARCHIVED = "archived"

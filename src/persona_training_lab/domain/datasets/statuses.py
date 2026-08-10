from enum import StrEnum


class DatasetVersionStatus(StrEnum):
    DRAFT = "draft"
    IMPORTED = "imported"
    VALIDATED = "validated"
    APPROVED = "approved_for_training"
    STRUCTURE_ERROR = "structure_error"
    VALIDATION_FAILED = "validation_failed"
    ARCHIVED = "archived"
    UNKNOWN = "unknown"


class DatasetReadinessStatus(StrEnum):
    AWAITING_VALIDATION = "awaiting_validation"
    AWAITING_AUTHOR_APPROVAL = "awaiting_author_approval"
    APPROVED = "approved_for_training"
    REQUIRES_FIX = "requires_fix"
    VALIDATION_FAILED = "validation_failed"

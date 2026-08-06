from enum import StrEnum


class ModelAvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ModelVersionStatus(StrEnum):
    UNKNOWN = "unknown"
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"
    FAILED = "failed"

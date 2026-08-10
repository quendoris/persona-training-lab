from enum import StrEnum


class ProfileStatus(StrEnum):
    READY = "ready"
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"
    UNKNOWN = "unknown"

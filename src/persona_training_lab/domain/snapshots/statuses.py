from enum import StrEnum


class SnapshotStatus(StrEnum):
    DRAFT = "draft"
    FROZEN = "frozen"
    TESTED = "tested"
    APPROVED = "approved"
    ARCHIVED = "archived"

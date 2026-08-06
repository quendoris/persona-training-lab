from enum import StrEnum


class EvaluationRunStatus(StrEnum):
    UNKNOWN = "unknown"
    CREATED = "created"
    RUNNING = "running"
    PARTIAL = "partial"
    FAILED = "failed"
    COMPLETED = "completed"

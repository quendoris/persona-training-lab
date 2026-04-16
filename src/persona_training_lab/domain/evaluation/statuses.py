from enum import StrEnum


class EvaluationRunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"

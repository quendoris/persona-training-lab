from enum import StrEnum


class TrainingRunStatus(StrEnum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"

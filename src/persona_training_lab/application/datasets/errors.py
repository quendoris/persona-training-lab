from __future__ import annotations

from enum import StrEnum

from persona_training_lab.shared.errors import PersonaTrainingLabError


class DatasetServiceErrorCode(StrEnum):
    FILE_NOT_FOUND = "file_not_found"
    ONLY_JSONL = "only_jsonl"
    SAVE_FAILED = "save_failed"
    NOT_FOUND = "not_found"


class DatasetServiceError(PersonaTrainingLabError):
    """Machine-semantic failure at the datasets application boundary."""

    def __init__(self, code: DatasetServiceErrorCode) -> None:
        self.code = code
        super().__init__(code.value)

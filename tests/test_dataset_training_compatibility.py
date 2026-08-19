from __future__ import annotations

import sqlite3
from pathlib import Path

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.domain.datasets.statuses import DatasetVersionStatus
from persona_training_lab.infrastructure.persistence.repositories.datasets import (
    SQLiteDatasetsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import create_minimal_schema


def test_messages_approval_requires_user_before_trainable_assistant(
    tmp_path: Path,
) -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    service = DatasetsService(
        datasets_repo=SQLiteDatasetsRepository(connection)
    )

    path = tmp_path / "reversed-chat.jsonl"
    path.write_text(
        '{"messages":['
        '{"role":"assistant","content":"I answered too early."},'
        '{"role":"user","content":"Now ask me."}'
        ']}\n',
        encoding="utf-8",
    )
    dataset = service.add_dataset_from_path(str(path))

    validation = service.validate_dataset(dataset.dataset_id)
    approval = service.approve_dataset(dataset.dataset_id)

    assert validation.status == DatasetVersionStatus.STRUCTURE_ERROR.value
    assert validation.invalid_rows == 1
    assert validation.errors_preview[0].code == "messages_missing_pair"
    assert not approval.ok
    persisted = service.list_datasets()[0]
    assert persisted.status == DatasetVersionStatus.STRUCTURE_ERROR.value

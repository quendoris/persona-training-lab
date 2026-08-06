from __future__ import annotations

import sqlite3

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.infrastructure.persistence.repositories.datasets import (
    SQLiteDatasetsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.viewmodels.datasets import DatasetsViewModel


def _build_service(connection: sqlite3.Connection) -> DatasetsService:
    repo = SQLiteDatasetsRepository(connection)
    return DatasetsService(datasets_repo=repo)


def test_datasets_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    rows = service.list_datasets()
    assert rows == []

    vm = DatasetsViewModel(datasets_service=service)
    dataset = vm.current_dataset()
    version = vm.current_version()
    assert dataset.dataset_id == "datasets_empty"
    assert dataset.subtitle.key == "datasets.empty.registry"
    assert version.status_code == "empty"
    assert vm.header_summary_model()[1].key == "datasets.header.summary"


def test_datasets_connector_single_row() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO datasets (id, title, subtitle, status, record_count, linked_profile, quality_summary, readiness, schema_name, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "ds_001",
            "curated_rose",
            "Реальный датасет из SQLite",
            "одобрен",
            74,
            "Mia core v3",
            "Сильная coherence по supportive-response оси",
            "Готов к обучению",
            "persona_json_v1",
            "2026-04-26T18:00:00Z",
        ),
    )
    connection.commit()

    service = _build_service(connection)
    rows = service.list_datasets()
    assert len(rows) == 1
    assert rows[0].dataset_id == "ds_001"
    assert rows[0].title == "curated_rose"
    assert rows[0].record_count == 74

    vm = DatasetsViewModel(datasets_service=service)
    dataset = vm.current_dataset()
    version = vm.current_version()
    assert dataset.dataset_id == "ds_001"
    assert dataset.title == "curated_rose"
    assert version.status == "одобрен"
    assert version.status_code == "approved"
    assert version.record_count == 74

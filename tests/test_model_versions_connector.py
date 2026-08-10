from __future__ import annotations

import sqlite3

from persona_training_lab.application.model_versions.service import (
    ModelVersionsService,
)
from persona_training_lab.domain.models.statuses import ModelVersionStatus
from persona_training_lab.infrastructure.persistence.repositories.model_versions import (
    SQLiteModelVersionsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.viewmodels.snapshots import SnapshotsViewModel
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


def _build_service(connection: sqlite3.Connection) -> ModelVersionsService:
    repo = SQLiteModelVersionsRepository(connection)
    return ModelVersionsService(model_versions_repo=repo)


def test_model_versions_connector_empty_state() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    rows = service.list_model_versions()
    assert rows == []

    training_vm = TrainingViewModel(model_versions_service=service)
    assert training_vm.versions_status_message == (
        "Версии личности пока не созданы"
    )
    assert training_vm.personality_versions[0].note == (
        "Версии личности пока не созданы"
    )

    snapshots_vm = SnapshotsViewModel(model_versions_service=service)
    assert snapshots_vm.current_snapshot().state_code == "empty"


def test_model_versions_connector_single_row() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    connection.execute(
        """
        INSERT INTO model_versions (
            id, title, status, base_model, profile_title, dataset_title,
            training_run_id, artifact_path, quality_summary, created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "mv_001",
            "Mia v3 Stable",
            "готов",
            "Qwen 2B",
            "Mia core v3",
            "curated_rose v07",
            "trn_014",
            "/artifacts/mv_001/model.safetensors",
            "Стабильная версия для тестирования личности",
            "2026-04-27T09:00:00Z",
            "2026-04-27T09:30:00Z",
        ),
    )
    connection.commit()

    service = _build_service(connection)
    rows = service.list_model_versions()
    assert len(rows) == 1
    assert rows[0].version_id == "mv_001"
    assert rows[0].training_run_id == "trn_014"
    assert rows[0].status == "готов"
    assert rows[0].status_code is ModelVersionStatus.READY

    training_vm = TrainingViewModel(model_versions_service=service)
    assert training_vm.versions_status_message == ""
    assert training_vm.personality_versions[0].title == "Mia v3 Stable"
    assert training_vm.personality_versions[0].status == "готов"
    assert training_vm.personality_versions[0].status_code == "ready"

    snapshots_vm = SnapshotsViewModel(model_versions_service=service)
    assert snapshots_vm.current_snapshot().snapshot_id == "mv_001"
    assert (
        snapshots_vm.current_snapshot().status_code
        is ModelVersionStatus.READY
    )


def test_created_model_version_persists_machine_semantics() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)

    service = _build_service(connection)
    created = service.create_from_training_run(
        training_run_id="trn_machine",
        base_model="Qwen",
        profile_title="Mia core",
        dataset_title="curated_v1",
        artifact_path="artifacts/trn_machine/model",
        quality_summary="   ",
    )

    assert created is not None
    assert created.status == ModelVersionStatus.READY.value
    assert created.status_code is ModelVersionStatus.READY
    assert created.quality_summary == ""

    row = connection.execute(
        """
        SELECT status, quality_summary
        FROM model_versions
        WHERE training_run_id = ?
        """,
        ("trn_machine",),
    ).fetchone()
    assert row is not None
    assert row["status"] == ModelVersionStatus.READY.value
    assert row["quality_summary"] == ""

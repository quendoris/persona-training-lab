from __future__ import annotations

import sqlite3

import pytest

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageProjectionService,
)
from persona_training_lab.application.lineage.projection import (
    LineageEntityKind,
    LineageRelation,
    LineageState,
)
from persona_training_lab.application.lineage.snapshot import (
    LineageDatasetRecord,
    LineageEvaluationRecord,
    LineageModelVersionRecord,
    LineageSourceSnapshot,
    LineageTrainingRunRecord,
)
from persona_training_lab.infrastructure.persistence.repositories.lineage_snapshot import (
    SQLiteLineageSnapshotRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.db import SQLiteDatabase
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


def _connections(tmp_path):
    database = SQLiteDatabase(tmp_path / "lineage.sqlite3")
    writer = database.connect()
    create_minimal_schema(writer)
    reader = database.connect_read_only()
    return writer, reader


def _insert_dataset(
    connection: sqlite3.Connection,
    *,
    dataset_id: str = "ds_1",
    title: str = "Dataset old",
    updated_at: str = "2026-08-06T10:00:00+00:00",
) -> None:
    connection.execute(
        """
        INSERT INTO datasets (
            id, title, subtitle, path, format, status,
            record_count, valid_count, invalid_count,
            linked_profile, quality_summary, validation_errors_preview,
            readiness, schema_name, created_at, updated_at
        ) VALUES (?, ?, '', ?, 'jsonl', 'Одобрен для обучения',
                  10, 10, 0, 'Mia', 'ok', '', 'ready', 'v1', ?, ?)
        """,
        (
            dataset_id,
            title,
            f"/datasets/{dataset_id}.jsonl",
            updated_at,
            updated_at,
        ),
    )


def _insert_training_run(
    connection: sqlite3.Connection,
    *,
    dataset_reference: str = "Dataset old",
    updated_at: str = "2026-08-06T10:01:00+00:00",
) -> None:
    connection.execute(
        """
        INSERT INTO training_runs (
            id, title, subtitle, status, base_model, profile,
            dataset_version, mode, epoch_progress, loss, speed,
            checkpoints_count, updated_at, progress, artifact_path,
            error_message
        ) VALUES (
            'trn_1', 'Training', '', 'completed', 'Qwen', 'Mia',
            ?, 'full', '3 / 3', '0.1', '1 it/s', '3', ?, 1.0,
            '/artifacts/trn_1', ''
        )
        """,
        (dataset_reference, updated_at),
    )


def test_read_only_connection_rejects_writes(tmp_path) -> None:
    writer, reader = _connections(tmp_path)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            reader.execute(
                "INSERT INTO projects VALUES ('p', 'P', 'ready', 'now')"
            )
    finally:
        reader.close()
        writer.close()


def test_repository_reads_one_consistent_wal_snapshot(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer, reader = _connections(tmp_path)
    _insert_dataset(writer)
    _insert_training_run(writer)
    writer.commit()
    repository = SQLiteLineageSnapshotRepository(reader)
    original = repository._read_datasets

    def read_datasets_then_commit_new_state():
        rows = original()
        writer.execute(
            """
            UPDATE datasets
            SET title = 'Dataset new',
                updated_at = '2026-08-06T11:00:00+00:00'
            WHERE id = 'ds_1'
            """
        )
        writer.execute(
            """
            UPDATE training_runs
            SET dataset_version = 'Dataset new',
                updated_at = '2026-08-06T11:01:00+00:00'
            WHERE id = 'trn_1'
            """
        )
        writer.commit()
        return rows

    monkeypatch.setattr(
        repository,
        "_read_datasets",
        read_datasets_then_commit_new_state,
    )
    first = repository.read_lineage_snapshot()
    monkeypatch.setattr(repository, "_read_datasets", original)
    second = repository.read_lineage_snapshot()

    assert first.datasets[0].title == "Dataset old"
    assert first.training_runs[0].dataset_version == "Dataset old"
    assert second.datasets[0].title == "Dataset new"
    assert second.training_runs[0].dataset_version == "Dataset new"

    reader.close()
    writer.close()


def test_repository_maps_all_lineage_tables(tmp_path) -> None:
    writer, reader = _connections(tmp_path)
    _insert_dataset(writer)
    _insert_training_run(writer)
    writer.execute(
        """
        INSERT INTO model_versions (
            id, title, status, base_model, profile_title, dataset_title,
            training_run_id, artifact_path, quality_summary,
            created_at, updated_at
        ) VALUES (
            'mdl_1', 'Weights', 'Готова', 'Qwen', 'Mia', 'Dataset old',
            'trn_1', '/artifacts/trn_1', 'ok',
            '2026-08-06T10:02:00+00:00',
            '2026-08-06T10:02:00+00:00'
        )
        """
    )
    writer.execute(
        """
        INSERT INTO experiments (id, title, subtitle, status, updated_at)
        VALUES (
            'evr_1', 'Portrait',
            'PORTRAIT: 1/1 · model_version=mdl_1 · '
            'artifact=/artifacts/trn_1',
            'Портрет собран', '2026-08-06T10:03:00+00:00'
        )
        """
    )
    writer.commit()

    snapshot = SQLiteLineageSnapshotRepository(
        reader
    ).read_lineage_snapshot()

    assert snapshot.datasets[0].dataset_id == "ds_1"
    assert snapshot.training_runs[0].run_id == "trn_1"
    assert snapshot.model_versions[0].version_id == "mdl_1"
    assert snapshot.evaluations[0].experiment_id == "evr_1"
    assert snapshot.evaluations[0].updated_at.endswith("+00:00")

    reader.close()
    writer.close()


class _SnapshotReader:
    def __init__(self, snapshot: LineageSourceSnapshot) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def read_lineage_snapshot(self) -> LineageSourceSnapshot:
        self.calls += 1
        return self.snapshot


def test_atomic_service_reads_once_and_normalizes_legacy_statuses() -> None:
    source = LineageSourceSnapshot(
        datasets=(
            LineageDatasetRecord(
                "ds_1",
                "Dataset",
                "Одобрен для обучения",
                "/datasets/ds_1.jsonl",
                "jsonl",
                10,
                10,
                0,
            ),
        ),
        training_runs=(
            LineageTrainingRunRecord(
                "trn_1",
                "Training",
                "Завершено",
                "Qwen",
                "Mia",
                "ds_1",
                "full",
                "1.0",
                "3 / 3",
                "0.1",
                "/artifacts/trn_1",
                "",
            ),
        ),
        model_versions=(
            LineageModelVersionRecord(
                "mdl_1",
                "Weights",
                "Готова",
                "Qwen",
                "Mia",
                "Dataset",
                "trn_1",
                "/artifacts/trn_1",
                "ok",
            ),
        ),
        evaluations=(
            LineageEvaluationRecord(
                "evr_1",
                "Portrait",
                "PORTRAIT: 1/1 · model_version=mdl_1 · "
                "artifact=/artifacts/trn_1",
                "Портрет собран",
            ),
        ),
    )
    reader = _SnapshotReader(source)

    result = AtomicLineageProjectionService(reader).build_snapshot()
    by_kind = {node.kind: node for node in result.projection.nodes}

    assert reader.calls == 1
    assert result.source is source
    assert by_kind[LineageEntityKind.DATASET].state is LineageState.READY
    assert by_kind[LineageEntityKind.TRAINING_RUN].state is LineageState.READY
    assert by_kind[LineageEntityKind.MODEL_VERSION].state is LineageState.READY
    assert by_kind[LineageEntityKind.EVALUATION_RUN].state is LineageState.READY
    assert any(
        edge.relation is LineageRelation.EVALUATES_VERSION
        for edge in result.projection.edges
    )

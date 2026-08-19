from __future__ import annotations

from pathlib import Path

from persona_training_lab.application.lineage.projection_builder import (
    build_lineage_projection,
)
from persona_training_lab.application.lineage.projection_model import (
    LineageEntityKind,
    LineageRelation,
    lineage_node_id,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.infrastructure.persistence.repositories.lineage_snapshot import (
    SQLiteLineageSnapshotRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.db import SQLiteDatabase
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


def _insert_dataset(connection, dataset_id: str) -> None:
    connection.execute(
        """
        INSERT INTO datasets (
            id, title, subtitle, path, format, status,
            record_count, valid_count, invalid_count,
            linked_profile, quality_summary, validation_errors_preview,
            readiness, schema_name, created_at, updated_at
        ) VALUES (?, 'Shared title', '', ?, 'jsonl', 'approved',
                  1, 1, 0, '', '', '', 'ready', 'jsonl_finetune_v1',
                  '2026-08-19T13:00:00+00:00',
                  '2026-08-19T13:00:00+00:00')
        """,
        (dataset_id, f"/datasets/{dataset_id}.jsonl"),
    )


def test_sqlite_lineage_uses_persisted_training_input_ids(tmp_path: Path) -> None:
    database = SQLiteDatabase(tmp_path / "lineage.sqlite3")
    writer = database.connect()
    create_minimal_schema(writer)
    _insert_dataset(writer, "ds_other")
    _insert_dataset(writer, "ds_target")
    writer.execute(
        """
        INSERT INTO training_runs (
            id, title, subtitle, status, base_model, profile,
            dataset_version, profile_id, dataset_id,
            mode, epoch_progress, loss, speed, checkpoints_count,
            updated_at, progress, artifact_path, error_message
        ) VALUES (
            'trn_exact', 'Exact run', '', 'completed', 'Qwen', 'Mia Core',
            'Shared title', 'prf_exact', 'ds_target',
            'full', '1 / 1', '0.1', 'full fine-tune', '01',
            '2026-08-19T13:01:00+00:00', 1.0,
            '/artifacts/trn_exact', ''
        )
        """
    )
    writer.commit()

    reader = database.connect_read_only()
    try:
        snapshot = SQLiteLineageSnapshotRepository(
            reader
        ).read_lineage_snapshot()
    finally:
        reader.close()
        writer.close()

    run = snapshot.training_runs[0]
    assert run.profile == "prf_exact"
    assert run.dataset_version == "ds_target"

    projection = build_lineage_projection(
        datasets=snapshot.datasets,
        training_runs=snapshot.training_runs,
        model_versions=snapshot.model_versions,
        evaluations=snapshot.evaluations,
    )
    run_node_id = lineage_node_id(
        LineageEntityKind.TRAINING_RUN,
        "trn_exact",
    )
    target_dataset_id = lineage_node_id(
        LineageEntityKind.DATASET,
        "ds_target",
    )
    other_dataset_id = lineage_node_id(
        LineageEntityKind.DATASET,
        "ds_other",
    )
    profile_node_id = lineage_node_id(
        LineageEntityKind.PERSONA_PROFILE,
        "prf_exact",
    )

    assert (
        target_dataset_id,
        run_node_id,
        LineageRelation.USES_DATASET,
    ) in {
        (edge.source_node_id, edge.target_node_id, edge.relation)
        for edge in projection.edges
    }
    assert all(
        not (
            edge.source_node_id == other_dataset_id
            and edge.target_node_id == run_node_id
            and edge.relation is LineageRelation.USES_DATASET
        )
        for edge in projection.edges
    )
    profile_node = projection.node(profile_node_id)
    assert profile_node is not None
    assert ResourceClaim("profile", "prf_exact") in profile_node.claims
    assert projection.unresolved == ()

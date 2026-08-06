from __future__ import annotations

import sqlite3

from persona_training_lab.application.lineage.snapshot import (
    LineageDatasetRecord,
    LineageEvaluationRecord,
    LineageModelVersionRecord,
    LineageSourceSnapshot,
    LineageTrainingRunRecord,
)
from persona_training_lab.infrastructure.persistence.sqlite.locking import (
    connection_lock,
)


class SQLiteLineageSnapshotRepository:
    """Read the complete lineage source set from one SQLite snapshot."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = connection_lock(connection)

    def read_lineage_snapshot(self) -> LineageSourceSnapshot:
        with self._lock:
            self._connection.execute("BEGIN DEFERRED")
            try:
                datasets = self._read_datasets()
                training_runs = self._read_training_runs()
                model_versions = self._read_model_versions()
                evaluations = self._read_evaluations()
                self._connection.execute("COMMIT")
            except Exception:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
                raise
        return LineageSourceSnapshot(
            datasets=datasets,
            training_runs=training_runs,
            model_versions=model_versions,
            evaluations=evaluations,
        )

    def _read_datasets(self) -> tuple[LineageDatasetRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT id, title, status, path, format,
                   record_count, valid_count, invalid_count, updated_at
            FROM datasets
            ORDER BY updated_at DESC, title ASC, id ASC
            """
        ).fetchall()
        return tuple(
            LineageDatasetRecord(
                dataset_id=str(row["id"] or ""),
                title=str(row["title"] or ""),
                status=str(row["status"] or ""),
                path=str(row["path"] or ""),
                format=str(row["format"] or ""),
                record_count=int(row["record_count"] or 0),
                valid_count=int(row["valid_count"] or 0),
                invalid_count=int(row["invalid_count"] or 0),
                updated_at=str(row["updated_at"] or ""),
            )
            for row in rows
        )

    def _read_training_runs(self) -> tuple[LineageTrainingRunRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT id, title, status, base_model, profile,
                   dataset_version, mode, progress, epoch_progress, loss,
                   artifact_path, error_message, updated_at
            FROM training_runs
            ORDER BY updated_at DESC, title ASC, id ASC
            """
        ).fetchall()
        return tuple(
            LineageTrainingRunRecord(
                run_id=str(row["id"] or ""),
                title=str(row["title"] or ""),
                status=str(row["status"] or ""),
                base_model=str(row["base_model"] or ""),
                profile=str(row["profile"] or ""),
                dataset_version=str(row["dataset_version"] or ""),
                mode=str(row["mode"] or ""),
                progress=str(row["progress"] or "0"),
                epoch_progress=str(row["epoch_progress"] or ""),
                loss=str(row["loss"] or ""),
                artifact_path=str(row["artifact_path"] or ""),
                error_message=str(row["error_message"] or ""),
                updated_at=str(row["updated_at"] or ""),
            )
            for row in rows
        )

    def _read_model_versions(self) -> tuple[LineageModelVersionRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT id, title, status, base_model, profile_title,
                   dataset_title, training_run_id, artifact_path,
                   quality_summary, updated_at
            FROM model_versions
            ORDER BY updated_at DESC, title ASC, id ASC
            """
        ).fetchall()
        return tuple(
            LineageModelVersionRecord(
                version_id=str(row["id"] or ""),
                title=str(row["title"] or ""),
                status=str(row["status"] or ""),
                base_model=str(row["base_model"] or ""),
                profile_title=str(row["profile_title"] or ""),
                dataset_title=str(row["dataset_title"] or ""),
                training_run_id=str(row["training_run_id"] or ""),
                artifact_path=str(row["artifact_path"] or ""),
                quality_summary=str(row["quality_summary"] or ""),
                updated_at=str(row["updated_at"] or ""),
            )
            for row in rows
        )

    def _read_evaluations(self) -> tuple[LineageEvaluationRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT id, title, subtitle, status, updated_at
            FROM experiments
            ORDER BY updated_at DESC, title ASC, id ASC
            """
        ).fetchall()
        return tuple(
            LineageEvaluationRecord(
                experiment_id=str(row["id"] or ""),
                title=str(row["title"] or ""),
                subtitle=str(row["subtitle"] or ""),
                status=str(row["status"] or ""),
                updated_at=str(row["updated_at"] or ""),
            )
            for row in rows
        )

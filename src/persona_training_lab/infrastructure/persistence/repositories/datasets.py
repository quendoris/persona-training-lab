from __future__ import annotations

import sqlite3

from persona_training_lab.application.datasets.status_mapping import (
    normalize_dataset_status,
)
from persona_training_lab.domain.datasets.statuses import (
    DatasetReadinessStatus,
    DatasetVersionStatus,
)


class SQLiteDatasetsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_datasets(self) -> list[dict[str, str | int]]:
        rows = self._connection.execute(
            """
            SELECT id, title, subtitle, path, format, status, record_count, valid_count, invalid_count,
                   quality_summary, validation_errors_preview, linked_profile, readiness, schema_name
            FROM datasets
            ORDER BY updated_at DESC, title ASC
            """
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_dataset(self, dataset_id: str) -> dict[str, str | int] | None:
        row = self._connection.execute(
            """
            SELECT id, title, subtitle, path, format, status, record_count, valid_count, invalid_count,
                   quality_summary, validation_errors_preview, linked_profile, readiness, schema_name
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def add_dataset(self, payload: dict[str, str | int]) -> None:
        self._connection.execute(
            """
            INSERT INTO datasets (
                id, title, subtitle, path, format, status,
                record_count, valid_count, invalid_count,
                quality_summary, validation_errors_preview,
                linked_profile, readiness, schema_name,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("id", ""),
                payload.get("title", ""),
                payload.get("subtitle", ""),
                payload.get("path", ""),
                payload.get("format", "jsonl"),
                payload.get("status", DatasetVersionStatus.IMPORTED.value),
                int(payload.get("record_count", 0)),
                int(payload.get("valid_count", 0)),
                int(payload.get("invalid_count", 0)),
                payload.get("quality_summary", ""),
                payload.get("validation_errors_preview", ""),
                payload.get("linked_profile", "—"),
                payload.get(
                    "readiness",
                    DatasetReadinessStatus.AWAITING_VALIDATION.value,
                ),
                payload.get("schema_name", "jsonl_finetune_v1"),
                payload.get("created_at", ""),
                payload.get("updated_at", ""),
            ),
        )
        self._connection.commit()

    def update_dataset_validation(
        self,
        dataset_id: str,
        payload: dict[str, str | int],
    ) -> None:
        self._connection.execute(
            """
            UPDATE datasets
            SET status = ?,
                record_count = ?,
                valid_count = ?,
                invalid_count = ?,
                quality_summary = ?,
                validation_errors_preview = ?,
                readiness = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.get("status", DatasetVersionStatus.IMPORTED.value),
                int(payload.get("record_count", 0)),
                int(payload.get("valid_count", 0)),
                int(payload.get("invalid_count", 0)),
                payload.get("quality_summary", ""),
                payload.get("validation_errors_preview", ""),
                self._readiness_from_status(
                    str(
                        payload.get(
                            "status",
                            DatasetVersionStatus.IMPORTED.value,
                        )
                    )
                ),
                payload.get("updated_at", ""),
                dataset_id,
            ),
        )
        self._connection.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, str | int]:
        return {
            "dataset_id": row["id"],
            "title": row["title"],
            "subtitle": row["subtitle"],
            "path": row["path"],
            "format": row["format"],
            "status": row["status"],
            "record_count": row["record_count"],
            "valid_count": row["valid_count"],
            "invalid_count": row["invalid_count"],
            "quality_summary": row["quality_summary"],
            "validation_errors_preview": row["validation_errors_preview"],
            "linked_profile": row["linked_profile"],
            "readiness": row["readiness"],
            "schema_name": row["schema_name"],
        }

    def _readiness_from_status(self, status: str) -> str:
        status_code = normalize_dataset_status(status)
        if status_code is DatasetVersionStatus.APPROVED:
            return DatasetReadinessStatus.APPROVED.value
        if status_code is DatasetVersionStatus.VALIDATED:
            return DatasetReadinessStatus.AWAITING_AUTHOR_APPROVAL.value
        if status_code is DatasetVersionStatus.STRUCTURE_ERROR:
            return DatasetReadinessStatus.REQUIRES_FIX.value
        if status_code is DatasetVersionStatus.VALIDATION_FAILED:
            return DatasetReadinessStatus.VALIDATION_FAILED.value
        return DatasetReadinessStatus.AWAITING_VALIDATION.value

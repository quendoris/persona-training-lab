from __future__ import annotations

import sqlite3


class SQLiteModelVersionsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_model_versions(self) -> list[dict[str, str]]:
        rows = self._connection.execute(
            """
            SELECT id, title, status, base_model, profile_title, dataset_title, training_run_id, artifact_path, quality_summary
            FROM model_versions
            ORDER BY updated_at DESC, title ASC
            """
        ).fetchall()
        return [
            {
                "version_id": row["id"],
                "title": row["title"],
                "status": row["status"],
                "base_model": row["base_model"],
                "profile_title": row["profile_title"],
                "dataset_title": row["dataset_title"],
                "training_run_id": row["training_run_id"],
                "artifact_path": row["artifact_path"],
                "quality_summary": row["quality_summary"],
            }
            for row in rows
        ]

from __future__ import annotations

import sqlite3

from persona_training_lab.infrastructure.persistence.sqlite.locking import (
    connection_lock,
)


class SQLiteModelVersionsRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = connection_lock(connection)

    def list_model_versions(self) -> list[dict[str, str]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, title, status, base_model, profile_title,
                       dataset_title, training_run_id, artifact_path,
                       quality_summary
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

    def create_model_version(self, payload: dict[str, str]) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO model_versions (
                    id, title, status, base_model, profile_title,
                    dataset_title, training_run_id, artifact_path,
                    quality_summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["title"],
                    payload["status"],
                    payload["base_model"],
                    payload["profile_title"],
                    payload["dataset_title"],
                    payload["training_run_id"],
                    payload["artifact_path"],
                    payload["quality_summary"],
                    payload.get("created_at", ""),
                    payload.get("updated_at", ""),
                ),
            )

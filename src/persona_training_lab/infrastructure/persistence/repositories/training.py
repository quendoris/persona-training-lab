from __future__ import annotations

import sqlite3


class SQLiteTrainingRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_training_runs(self) -> list[dict[str, str]]:
        rows = self._connection.execute(
            """
            SELECT id, title, subtitle, status, base_model, profile, dataset_version, mode, epoch_progress, loss, speed, checkpoints_count
            FROM training_runs
            ORDER BY updated_at DESC, title ASC
            """
        ).fetchall()
        return [
            {
                "run_id": row["id"],
                "title": row["title"],
                "subtitle": row["subtitle"],
                "status": row["status"],
                "base_model": row["base_model"],
                "profile": row["profile"],
                "dataset_version": row["dataset_version"],
                "mode": row["mode"],
                "epoch_progress": row["epoch_progress"],
                "loss": row["loss"],
                "speed": row["speed"],
                "checkpoints_count": row["checkpoints_count"],
            }
            for row in rows
        ]

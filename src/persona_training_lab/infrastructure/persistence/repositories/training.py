from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from persona_training_lab.infrastructure.persistence.sqlite.locking import connection_lock


class SQLiteTrainingRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = connection_lock(connection)

    def list_training_runs(self) -> list[dict[str, str]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, title, subtitle, status, base_model, profile,
                       dataset_version, profile_id, dataset_id,
                       profile_sha256, dataset_sha256, mode,
                       epochs, batch_size, learning_rate,
                       epoch_progress, loss, speed, checkpoints_count, progress,
                       started_at, finished_at, artifact_path, error_message
                FROM training_runs
                ORDER BY updated_at DESC, title ASC
                """
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def create_training_run(self, payload: dict[str, str]) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO training_runs (
                    id, title, subtitle, status, base_model, profile,
                    dataset_version, profile_id, dataset_id,
                    profile_sha256, dataset_sha256, mode,
                    epochs, batch_size, learning_rate,
                    epoch_progress, loss, speed, checkpoints_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("id", ""),
                    payload.get("title", ""),
                    payload.get("subtitle", ""),
                    payload.get("status", ""),
                    payload.get("base_model", ""),
                    payload.get("profile", ""),
                    payload.get("dataset_version", ""),
                    payload.get("profile_id", ""),
                    payload.get("dataset_id", ""),
                    payload.get("profile_sha256", ""),
                    payload.get("dataset_sha256", ""),
                    payload.get("mode", ""),
                    int(payload.get("epochs", "1") or 1),
                    int(payload.get("batch_size", "1") or 1),
                    float(payload.get("learning_rate", "0.0001") or 0.0001),
                    payload.get("epoch_progress", ""),
                    payload.get("loss", ""),
                    payload.get("speed", ""),
                    payload.get("checkpoints_count", "00"),
                    payload.get("updated_at", ""),
                ),
            )

    def get_training_run(self, run_id: str) -> dict[str, str] | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, title, subtitle, status, base_model, profile,
                       dataset_version, profile_id, dataset_id,
                       profile_sha256, dataset_sha256, mode,
                       epochs, batch_size, learning_rate,
                       epoch_progress, loss, speed, checkpoints_count, progress,
                       started_at, finished_at, artifact_path, error_message
                FROM training_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def update_training_run_runtime(
        self,
        run_id: str,
        payload: dict[str, str],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connection:
            self._connection.execute(
                """
                UPDATE training_runs
                SET status = ?, epoch_progress = ?, progress = ?, loss = ?,
                    speed = ?, checkpoints_count = ?, started_at = ?,
                    finished_at = ?, artifact_path = ?, error_message = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.get("status", ""),
                    payload.get("epoch_progress", ""),
                    float(payload.get("progress", "0") or 0),
                    payload.get("loss", ""),
                    payload.get("speed", ""),
                    payload.get("checkpoints_count", "00"),
                    payload.get("started_at", ""),
                    payload.get("finished_at", ""),
                    payload.get("artifact_path", ""),
                    payload.get("error_message", ""),
                    now,
                    run_id,
                ),
            )

    def add_training_log(
        self,
        run_id: str,
        level: str,
        message: str,
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO training_logs (id, run_id, level, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    f"log_{uuid4().hex[:12]}",
                    run_id,
                    level,
                    message,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_training_logs(self, run_id: str, limit: int = 100) -> list[str]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT level, message
                FROM training_logs
                WHERE run_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
        return [f"[{row['level']}] {row['message']}" for row in reversed(rows)]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, str]:
        return {
            "run_id": row["id"],
            "title": row["title"],
            "subtitle": row["subtitle"],
            "status": row["status"],
            "base_model": row["base_model"],
            "profile": row["profile"],
            "dataset_version": row["dataset_version"],
            "profile_id": row["profile_id"],
            "dataset_id": row["dataset_id"],
            "profile_sha256": row["profile_sha256"],
            "dataset_sha256": row["dataset_sha256"],
            "mode": row["mode"],
            "epochs": str(row["epochs"]),
            "batch_size": str(row["batch_size"]),
            "learning_rate": str(row["learning_rate"]),
            "epoch_progress": row["epoch_progress"],
            "loss": row["loss"],
            "speed": row["speed"],
            "checkpoints_count": row["checkpoints_count"],
            "progress": str(row["progress"]),
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "artifact_path": row["artifact_path"],
            "error_message": row["error_message"],
        }

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4


class SQLiteTrainingRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_training_runs(self) -> list[dict[str, str]]:
        rows = self._connection.execute(
            """
            SELECT id, title, subtitle, status, base_model, profile, dataset_version, mode, epoch_progress, loss, speed, checkpoints_count, progress, started_at, finished_at, artifact_path, error_message
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
                "progress": str(row["progress"]),
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "artifact_path": row["artifact_path"],
                "error_message": row["error_message"],
            }
            for row in rows
        ]

    def create_training_run(self, payload: dict[str, str]) -> None:
        self._connection.execute(
            """
            INSERT INTO training_runs (
                id, title, subtitle, status, base_model, profile, dataset_version,
                mode, epoch_progress, loss, speed, checkpoints_count, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("id", ""),
                payload.get("title", ""),
                payload.get("subtitle", ""),
                payload.get("status", ""),
                payload.get("base_model", ""),
                payload.get("profile", ""),
                payload.get("dataset_version", ""),
                payload.get("mode", ""),
                payload.get("epoch_progress", ""),
                payload.get("loss", ""),
                payload.get("speed", ""),
                payload.get("checkpoints_count", "00"),
                payload.get("updated_at", ""),
            ),
        )
        self._connection.commit()

    def get_training_run(self, run_id: str) -> dict[str, str] | None:
        row = self._connection.execute(
            """
            SELECT id, title, subtitle, status, base_model, profile, dataset_version, mode, epoch_progress, loss, speed, checkpoints_count, progress, started_at, finished_at, artifact_path, error_message
            FROM training_runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return {
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
            "progress": str(row["progress"]),
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "artifact_path": row["artifact_path"],
            "error_message": row["error_message"],
        }

    def update_training_run_runtime(self, run_id: str, payload: dict[str, str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._connection.execute(
            """
            UPDATE training_runs
            SET status = ?, epoch_progress = ?, progress = ?, loss = ?, speed = ?, checkpoints_count = ?,
                started_at = ?, finished_at = ?, artifact_path = ?, error_message = ?, updated_at = ?
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
        self._connection.commit()

    def add_training_log(self, run_id: str, level: str, message: str) -> None:
        self._connection.execute(
            "INSERT INTO training_logs (id, run_id, level, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (f"log_{uuid4().hex[:12]}", run_id, level, message, datetime.now(timezone.utc).isoformat()),
        )
        self._connection.commit()

    def list_training_logs(self, run_id: str, limit: int = 100) -> list[str]:
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

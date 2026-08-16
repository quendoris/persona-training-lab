from __future__ import annotations

import sqlite3

from persona_training_lab.infrastructure.persistence.sqlite.locking import (
    connection_lock,
)


class SQLiteAnalysisRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = connection_lock(connection)

    def list_analysis_results(self) -> list[dict[str, str]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT
                    id, title, subtitle,
                    left_title, left_subtitle, left_profile_match, left_stability, left_contradiction,
                    right_title, right_subtitle, right_profile_match, right_stability, right_contradiction,
                    delta_profile_match, delta_stability, delta_contradiction,
                    insight_1, insight_2, insight_3,
                    delta_1, delta_2, delta_3,
                    sample_1_title, sample_1_left, sample_1_right,
                    sample_2_title, sample_2_left, sample_2_right
                FROM analysis_results
                ORDER BY updated_at DESC, title ASC
                """
            ).fetchall()
        return [
            {
                "result_id": row["id"],
                "title": row["title"],
                "subtitle": row["subtitle"],
                "left_title": row["left_title"],
                "left_subtitle": row["left_subtitle"],
                "left_profile_match": row["left_profile_match"],
                "left_stability": row["left_stability"],
                "left_contradiction": row["left_contradiction"],
                "right_title": row["right_title"],
                "right_subtitle": row["right_subtitle"],
                "right_profile_match": row["right_profile_match"],
                "right_stability": row["right_stability"],
                "right_contradiction": row["right_contradiction"],
                "delta_profile_match": row["delta_profile_match"],
                "delta_stability": row["delta_stability"],
                "delta_contradiction": row["delta_contradiction"],
                "insight_1": row["insight_1"],
                "insight_2": row["insight_2"],
                "insight_3": row["insight_3"],
                "delta_1": row["delta_1"],
                "delta_2": row["delta_2"],
                "delta_3": row["delta_3"],
                "sample_1_title": row["sample_1_title"],
                "sample_1_left": row["sample_1_left"],
                "sample_1_right": row["sample_1_right"],
                "sample_2_title": row["sample_2_title"],
                "sample_2_left": row["sample_2_left"],
                "sample_2_right": row["sample_2_right"],
            }
            for row in rows
        ]

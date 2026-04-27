from __future__ import annotations

import sqlite3


def create_minimal_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS ui_preferences (
            id TEXT PRIMARY KEY,
            theme TEXT NULL,
            accent_palette TEXT NULL,
            button_style_preset TEXT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS event_log (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            entity_kind TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            correlation_id TEXT NULL,
            causation_id TEXT NULL,
            payload_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_event_log_entity
        ON event_log(entity_kind, entity_id, occurred_at);

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_projects_updated
        ON projects(updated_at DESC);

        CREATE TABLE IF NOT EXISTS persona_profiles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_persona_profiles_updated
        ON persona_profiles(updated_at DESC);

        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_agents_updated
        ON agents(updated_at DESC);

        CREATE TABLE IF NOT EXISTS experiments (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_experiments_updated
        ON experiments(updated_at DESC);

        CREATE TABLE IF NOT EXISTS datasets (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            status TEXT NOT NULL,
            record_count INTEGER NOT NULL,
            linked_profile TEXT NOT NULL,
            quality_summary TEXT NOT NULL,
            readiness TEXT NOT NULL,
            schema_name TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_datasets_updated
        ON datasets(updated_at DESC);

        CREATE TABLE IF NOT EXISTS training_runs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            status TEXT NOT NULL,
            base_model TEXT NOT NULL,
            profile TEXT NOT NULL,
            dataset_version TEXT NOT NULL,
            mode TEXT NOT NULL,
            epoch_progress TEXT NOT NULL,
            loss TEXT NOT NULL,
            speed TEXT NOT NULL,
            checkpoints_count TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_training_runs_updated
        ON training_runs(updated_at DESC);

        CREATE TABLE IF NOT EXISTS analysis_results (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            left_title TEXT NOT NULL,
            left_subtitle TEXT NOT NULL,
            left_profile_match TEXT NOT NULL,
            left_stability TEXT NOT NULL,
            left_contradiction TEXT NOT NULL,
            right_title TEXT NOT NULL,
            right_subtitle TEXT NOT NULL,
            right_profile_match TEXT NOT NULL,
            right_stability TEXT NOT NULL,
            right_contradiction TEXT NOT NULL,
            delta_profile_match TEXT NOT NULL,
            delta_stability TEXT NOT NULL,
            delta_contradiction TEXT NOT NULL,
            insight_1 TEXT NOT NULL,
            insight_2 TEXT NOT NULL,
            insight_3 TEXT NOT NULL,
            delta_1 TEXT NOT NULL,
            delta_2 TEXT NOT NULL,
            delta_3 TEXT NOT NULL,
            sample_1_title TEXT NOT NULL,
            sample_1_left TEXT NOT NULL,
            sample_1_right TEXT NOT NULL,
            sample_2_title TEXT NOT NULL,
            sample_2_left TEXT NOT NULL,
            sample_2_right TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_analysis_results_updated
        ON analysis_results(updated_at DESC);

        CREATE TABLE IF NOT EXISTS model_versions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            base_model TEXT NOT NULL,
            profile_title TEXT NOT NULL,
            dataset_title TEXT NOT NULL,
            training_run_id TEXT NOT NULL,
            artifact_path TEXT NOT NULL,
            quality_summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_model_versions_updated
        ON model_versions(updated_at DESC);
        """
    )
    connection.commit()

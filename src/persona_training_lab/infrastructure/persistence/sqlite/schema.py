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
            description TEXT NOT NULL DEFAULT '',
            communication_style TEXT NOT NULL DEFAULT '',
            principles TEXT NOT NULL DEFAULT '',
            constraints TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT '',
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
            path TEXT NOT NULL DEFAULT '',
            format TEXT NOT NULL DEFAULT 'jsonl',
            status TEXT NOT NULL,
            record_count INTEGER NOT NULL,
            valid_count INTEGER NOT NULL DEFAULT 0,
            invalid_count INTEGER NOT NULL DEFAULT 0,
            linked_profile TEXT NOT NULL,
            quality_summary TEXT NOT NULL,
            validation_errors_preview TEXT NOT NULL DEFAULT '',
            readiness TEXT NOT NULL,
            schema_name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT '',
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
    _ensure_profile_columns(connection)
    _ensure_dataset_columns(connection)
    _ensure_training_run_columns(connection)
    _ensure_training_log_table(connection)
    connection.commit()


def _ensure_profile_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(persona_profiles)").fetchall()
    }
    additions = [
        ("description", "TEXT NOT NULL DEFAULT ''"),
        ("communication_style", "TEXT NOT NULL DEFAULT ''"),
        ("principles", "TEXT NOT NULL DEFAULT ''"),
        ("constraints", "TEXT NOT NULL DEFAULT ''"),
        ("notes", "TEXT NOT NULL DEFAULT ''"),
        ("created_at", "TEXT NOT NULL DEFAULT ''"),
    ]
    for name, definition in additions:
        if name not in columns:
            connection.execute(f"ALTER TABLE persona_profiles ADD COLUMN {name} {definition}")


def _ensure_dataset_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(datasets)").fetchall()
    }
    additions = [
        ("path", "TEXT NOT NULL DEFAULT ''"),
        ("format", "TEXT NOT NULL DEFAULT 'jsonl'"),
        ("valid_count", "INTEGER NOT NULL DEFAULT 0"),
        ("invalid_count", "INTEGER NOT NULL DEFAULT 0"),
        ("validation_errors_preview", "TEXT NOT NULL DEFAULT ''"),
        ("created_at", "TEXT NOT NULL DEFAULT ''"),
    ]
    for name, definition in additions:
        if name not in columns:
            connection.execute(f"ALTER TABLE datasets ADD COLUMN {name} {definition}")


def _ensure_training_run_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(training_runs)").fetchall()}
    additions = [
        ("started_at", "TEXT NOT NULL DEFAULT ''"),
        ("finished_at", "TEXT NOT NULL DEFAULT ''"),
        ("progress", "REAL NOT NULL DEFAULT 0"),
    ]
    for name, definition in additions:
        if name not in columns:
            connection.execute(f"ALTER TABLE training_runs ADD COLUMN {name} {definition}")


def _ensure_training_log_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS training_logs (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageProjectionService,
    AtomicLineageSnapshot,
)
from persona_training_lab.infrastructure.persistence.repositories.lineage_snapshot import (
    SQLiteLineageSnapshotRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.db import SQLiteDatabase


@dataclass(slots=True)
class SQLiteLineageProjectionLoader:
    """Lazily owns one read-only SQLite connection in its calling thread."""

    database_path: Path
    _connection: sqlite3.Connection | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _service: AtomicLineageProjectionService | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _closed: bool = field(default=False, init=False, repr=False)

    def build_snapshot(self) -> AtomicLineageSnapshot:
        if self._closed:
            raise RuntimeError("Lineage projection loader is closed")
        service = self._service
        if service is None:
            connection = SQLiteDatabase(
                self.database_path
            ).connect_read_only()
            self._connection = connection
            service = AtomicLineageProjectionService(
                SQLiteLineageSnapshotRepository(connection)
            )
            self._service = service
        return service.build_snapshot()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        connection = self._connection
        self._service = None
        self._connection = None
        if connection is not None:
            connection.close()

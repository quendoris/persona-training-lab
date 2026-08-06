from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteDatabase:
    def __init__(self, path: Path) -> None:
        self._path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._path,
            timeout=30.0,
            check_same_thread=False,
        )
        self._configure(connection, writable=True)
        return connection

    def connect_read_only(self) -> sqlite3.Connection:
        uri = f"file:{self._path.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(
            uri,
            uri=True,
            timeout=30.0,
            check_same_thread=False,
        )
        self._configure(connection, writable=False)
        return connection

    @staticmethod
    def _configure(
        connection: sqlite3.Connection,
        *,
        writable: bool,
    ) -> None:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        if writable:
            connection.execute("PRAGMA journal_mode = WAL;")
            connection.execute("PRAGMA synchronous = NORMAL;")
        else:
            connection.execute("PRAGMA query_only = ON;")
        connection.execute("PRAGMA busy_timeout = 5000;")

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise

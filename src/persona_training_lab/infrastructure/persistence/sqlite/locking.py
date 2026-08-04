from __future__ import annotations

import sqlite3
from threading import RLock


_REGISTRY_LOCK = RLock()
_CONNECTION_LOCKS: dict[int, RLock] = {}


def connection_lock(connection: sqlite3.Connection) -> RLock:
    """Return one process-local lock shared by every repository on a connection."""

    key = id(connection)
    with _REGISTRY_LOCK:
        lock = _CONNECTION_LOCKS.get(key)
        if lock is None:
            lock = RLock()
            _CONNECTION_LOCKS[key] = lock
        return lock

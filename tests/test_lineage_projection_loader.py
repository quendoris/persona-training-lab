from __future__ import annotations

import pytest

from persona_training_lab.infrastructure.persistence.lineage_loader import (
    SQLiteLineageProjectionLoader,
)
from persona_training_lab.infrastructure.persistence.sqlite.db import SQLiteDatabase
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


def test_loader_opens_read_connection_lazily_and_reuses_it(tmp_path) -> None:
    path = tmp_path / "lineage.sqlite3"
    writer = SQLiteDatabase(path).connect()
    create_minimal_schema(writer)
    writer.close()
    loader = SQLiteLineageProjectionLoader(path)

    assert loader._connection is None
    first = loader.build_snapshot()
    connection = loader._connection
    second = loader.build_snapshot()

    assert connection is not None
    assert loader._connection is connection
    assert first.projection.content_revision == second.projection.content_revision

    loader.close()
    assert loader._connection is None


def test_closed_loader_never_reopens_persistence(tmp_path) -> None:
    path = tmp_path / "lineage.sqlite3"
    writer = SQLiteDatabase(path).connect()
    create_minimal_schema(writer)
    writer.close()
    loader = SQLiteLineageProjectionLoader(path)

    loader.build_snapshot()
    loader.close()
    loader.close()

    with pytest.raises(RuntimeError, match="closed"):
        loader.build_snapshot()

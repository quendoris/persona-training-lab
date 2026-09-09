from __future__ import annotations

import sqlite3

import pytest

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.infrastructure.persistence.repositories.lineage_resource_links import (
    SQLiteLineageResourceLinksRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


def _repository() -> tuple[sqlite3.Connection, SQLiteLineageResourceLinksRepository]:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_minimal_schema(connection)
    return connection, SQLiteLineageResourceLinksRepository(connection)


def test_replace_links_rolls_back_delete_when_insert_fails() -> None:
    connection, repository = _repository()
    old = (ResourceClaim("dataset", "ds_old", "read"),)
    duplicate = ResourceClaim("model_version", "mdl_new", "read")
    repository.replace_links("branch_001", old)

    with pytest.raises(sqlite3.IntegrityError):
        repository.replace_links(
            "branch_001",
            (duplicate, duplicate),
        )

    assert repository.list_links("branch_001") == old
    connection.close()


def test_projection_reconciliation_rolls_back_all_nodes_and_stale_deletes() -> None:
    connection, repository = _repository()
    old_a = (ResourceClaim("dataset", "ds_a_old", "read"),)
    old_stale = (ResourceClaim("model_version", "mdl_stale", "read"),)
    repository.replace_links("dataset:ds_a", old_a)
    repository.replace_links("training:stale", old_stale)

    new_a = (ResourceClaim("dataset", "ds_a_new", "read"),)
    duplicate = ResourceClaim("training_run", "trn_b", "read")

    with pytest.raises(sqlite3.IntegrityError):
        repository.reconcile_projection_links(
            {
                "dataset:ds_a": new_a,
                "training:trn_b": (duplicate, duplicate),
            },
            ("training:stale",),
        )

    assert repository.list_links("dataset:ds_a") == old_a
    assert repository.list_links("training:trn_b") == ()
    assert repository.list_links("training:stale") == old_stale
    connection.close()

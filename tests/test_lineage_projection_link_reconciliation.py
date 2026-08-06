from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.infrastructure.persistence.repositories.lineage_resource_links import (
    SQLiteLineageResourceLinksRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.db import SQLiteDatabase
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


def _repository(tmp_path) -> tuple[
    sqlite3.Connection,
    SQLiteLineageResourceLinksRepository,
]:
    connection = SQLiteDatabase(tmp_path / "links.sqlite3").connect()
    create_minimal_schema(connection)
    return connection, SQLiteLineageResourceLinksRepository(connection)


def test_projection_reconciliation_updates_current_and_forgets_stale_nodes(
    tmp_path,
) -> None:
    connection, repository = _repository(tmp_path)
    safety = LineageRuntimeSafety(repository, SimpleNamespace())
    try:
        first_ids = safety.reconcile_projection(
            {
                "snapshot": (
                    ResourceClaim("model_version", "mdl_1", "write"),
                ),
                "version:old": (
                    ResourceClaim("model_version", "mdl_old", "read"),
                ),
            }
        )
        second_ids = safety.reconcile_projection(
            {
                "snapshot": (
                    ResourceClaim("model_version", "mdl_2", "write"),
                    ResourceClaim("artifact_path", "/models/mdl_2", "read"),
                ),
            },
            first_ids,
        )

        assert second_ids == ("snapshot",)
        assert repository.list_links("version:old") == ()
        assert repository.list_links("snapshot") == (
            ResourceClaim("artifact_path", "/models/mdl_2", "read"),
            ResourceClaim("model_version", "mdl_2", "read"),
        )
    finally:
        connection.close()


def test_reconciliation_rolls_back_every_node_when_one_claim_is_invalid(
    tmp_path,
) -> None:
    connection, repository = _repository(tmp_path)
    original = (ResourceClaim("model_version", "mdl_stable", "read"),)
    repository.replace_links("snapshot", original)
    invalid = SimpleNamespace(
        resource_kind="artifact_path",
        resource_id="/broken",
        access_mode="invalid",
    )
    try:
        with pytest.raises(sqlite3.IntegrityError):
            repository.reconcile_projection_links(
                {
                    "snapshot": (
                        ResourceClaim("model_version", "mdl_new", "read"),
                    ),
                    "version:broken": (invalid,),
                },
                (),
            )

        assert repository.list_links("snapshot") == original
        assert repository.list_links("version:broken") == ()
    finally:
        connection.close()

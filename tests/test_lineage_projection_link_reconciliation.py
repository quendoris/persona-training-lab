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
from persona_training_lab.ui.agents.atomic_lineage_public import (
    build_empty_lineage,
)
from persona_training_lab.ui.agents.screen_background_reconciled import (
    AgentsScreen as ReconciledAgentsScreen,
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


def test_first_reconciliation_cleans_old_projection_but_keeps_local_branch(
    tmp_path,
) -> None:
    connection, repository = _repository(tmp_path)
    safety = LineageRuntimeSafety(repository, SimpleNamespace())
    old_projection = (
        ResourceClaim("model_version", "mdl_removed", "read"),
    )
    local_branch = (
        ResourceClaim("model_version", "mdl_parent", "read"),
    )
    repository.replace_links("version:mdl_removed", old_projection)
    repository.replace_links("branch_001", local_branch)
    try:
        safety.reconcile_projection(
            {
                "snapshot": (
                    ResourceClaim("model_version", "mdl_current", "read"),
                ),
            },
            None,
        )

        assert repository.list_links("version:mdl_removed") == ()
        assert repository.list_links("branch_001") == local_branch
        assert repository.list_links("snapshot") == (
            ResourceClaim("model_version", "mdl_current", "read"),
        )
    finally:
        connection.close()


def test_placeholder_projection_never_mutates_registry_before_last_good() -> None:
    calls: list[object] = []

    class _Safety:
        def reconcile_projection(self, resources, previous):
            calls.append((resources, previous))
            return tuple(sorted(resources))

    coordinator = SimpleNamespace(last_good=None)
    screen = SimpleNamespace(
        _lineage_runtime_safety=_Safety(),
        _real_projection=build_empty_lineage(),
        _lineage_refresh_coordinator=coordinator,
        _bound_projection_node_ids=None,
    )

    ReconciledAgentsScreen._bind_projection_resources(screen)  # type: ignore[arg-type]
    assert calls == []

    coordinator.last_good = object()
    ReconciledAgentsScreen._bind_projection_resources(screen)  # type: ignore[arg-type]
    assert len(calls) == 1
    assert screen._bound_projection_node_ids == (
        "base",
        "dataset",
        "delta",
        "portrait",
        "snapshot",
        "training",
    )


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

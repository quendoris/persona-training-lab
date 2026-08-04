from __future__ import annotations

import sqlite3

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.operations import (
    ResourceClaim,
    RuntimeOperationCoordinator,
)
from persona_training_lab.infrastructure.persistence.repositories.lineage_resource_links import (
    SQLiteLineageResourceLinksRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.runtime_operations import (
    SQLiteRuntimeOperationsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)


def _services() -> tuple[
    sqlite3.Connection,
    RuntimeOperationCoordinator,
    LineageRuntimeSafety,
]:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_minimal_schema(connection)
    operations = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(connection)
    )
    safety = LineageRuntimeSafety(
        SQLiteLineageResourceLinksRepository(connection),
        operations,
    )
    return connection, operations, safety


def test_custom_branch_inherits_real_model_resources() -> None:
    _connection, _operations, safety = _services()
    safety.bind_node(
        "snapshot",
        (
            ResourceClaim("model_version", "mdl_001", "read"),
            ResourceClaim("artifact_path", "/models/mdl_001", "read"),
        ),
    )

    inherited = safety.inherit_node("branch_001", "snapshot")

    assert inherited == (
        ResourceClaim("artifact_path", "/models/mdl_001", "read"),
        ResourceClaim("model_version", "mdl_001", "read"),
    )
    assert safety.links_for_node("branch_001") == inherited


def test_active_portrait_blocks_deleting_linked_branch() -> None:
    _connection, operations, safety = _services()
    safety.bind_node(
        "branch_001",
        (
            ResourceClaim("model_version", "mdl_001", "read"),
            ResourceClaim("artifact_path", "/models/mdl_001", "read"),
        ),
    )
    lease = operations.begin(
        operation_kind="personality_test",
        subject_kind="experiment",
        subject_id="evr_001",
        claims=(
            ResourceClaim("model_version", "mdl_001", "read"),
            ResourceClaim("artifact_path", "/models/mdl_001", "read"),
        ),
    )

    blockers = safety.deletion_blockers(("branch_001",))

    assert {item.claim.resource_kind for item in blockers} == {
        "artifact_path",
        "model_version",
    }
    assert "personality_test" in safety.blocker_text(blockers)
    lease.succeed()
    assert safety.deletion_blockers(("branch_001",)) == ()


def test_forgetting_subtree_links_is_atomic() -> None:
    _connection, _operations, safety = _services()
    claim = ResourceClaim("model_version", "mdl_001", "read")
    safety.bind_node("branch_001", (claim,))
    safety.inherit_node("branch_002", "branch_001")

    assert safety.forget_nodes(("branch_001", "branch_002")) == 2
    assert safety.links_for_node("branch_001") == ()
    assert safety.links_for_node("branch_002") == ()

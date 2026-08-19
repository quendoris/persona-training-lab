from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.atomic import (
    RuntimeOperationCoordinator,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.infrastructure.persistence.repositories.lineage_resource_links import (
    SQLiteLineageResourceLinksRepository,
)
from persona_training_lab.infrastructure.persistence.repositories.runtime_operations_atomic import (
    SQLiteRuntimeOperationsRepository,
)
from persona_training_lab.infrastructure.persistence.sqlite.schema import (
    create_minimal_schema,
)
from persona_training_lab.ui.agents.branch_deletion import (
    BranchDeletionController,
    BranchDeletionPlan,
    BranchDeletionResult,
    BranchDeletionStatus,
)
from persona_training_lab.ui.agents.lineage_state import HistoryTransition
from persona_training_lab.ui.agents.lineage_state_atomic import (
    AtomicLineageStateStore,
)
from persona_training_lab.ui.agents.runtime_policy import LineageBranchTransactions
from persona_training_lab.ui.agents.screen_workspace_composition import (
    AgentsScreen as WorkspaceCompositionAgentsScreen,
)


def _connect(path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=2.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 2000")
    return connection


def test_atomic_delete_history_metadata_survives_undo_redo(tmp_path) -> None:
    path = tmp_path / "lineage-state.json"
    state = AtomicLineageStateStore(path)
    branch_id = state.continue_from("snapshot")
    metadata = {
        "kind": "branch_delete_v1",
        "subject_node_id": branch_id,
        "removed_ids": [branch_id],
        "resource_links": {
            branch_id: [
                {
                    "resource_kind": "model_version",
                    "resource_id": "mdl_001",
                    "access_mode": "read",
                }
            ]
        },
    }

    state.stage_history_metadata(metadata)
    assert state.delete_subtree(branch_id) == (branch_id,)

    undo_preview = state.undo_preview()
    assert undo_preview is not None
    assert undo_preview.action_code == "branch_delete"
    assert undo_preview.direction == "undo"
    assert undo_preview.metadata == metadata

    undone = state.undo_only()
    assert undone is not None
    assert undone.action_code == "branch_delete"
    assert state.is_custom_node(branch_id) is True

    redo_preview = state.history_toggle_preview()
    assert redo_preview is not None
    assert redo_preview.action_code == "branch_delete"
    assert redo_preview.direction == "redo"
    assert redo_preview.metadata == metadata

    redone = state.redo_last_action()
    assert redone is not None
    assert redone.action_code == "branch_delete"
    assert state.is_custom_node(branch_id) is False

    reloaded = AtomicLineageStateStore(path)
    final_preview = reloaded.undo_preview()
    assert final_preview is not None
    assert final_preview.metadata == metadata


def test_controller_delete_history_restores_exact_resource_links(tmp_path) -> None:
    database_path = tmp_path / "runtime.sqlite3"
    connection = _connect(database_path)
    create_minimal_schema(connection)
    operations = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(connection)
    )
    safety = LineageRuntimeSafety(
        SQLiteLineageResourceLinksRepository(connection),
        operations,
    )
    transactions = LineageBranchTransactions(safety)
    state = AtomicLineageStateStore(tmp_path / "lineage-state.json")
    root_id = state.continue_from("snapshot")
    child_id = state.continue_from(root_id)
    root_links = (
        ResourceClaim("model_version", "mdl_001", "read"),
        ResourceClaim("artifact_path", "/models/mdl_001", "read"),
    )
    normalized_links = tuple(sorted(root_links))
    safety.bind_node(root_id, root_links)
    safety.inherit_node(child_id, root_id)

    controller = BranchDeletionController(state, transactions)
    plan = controller.prepare(
        root_id,
        node_title="Branch",
        parent_id="snapshot",
        graph_current_id="snapshot",
    )
    assert plan is not None
    deleted = controller.execute(plan, layout_snapshot={"schema": 1})
    assert deleted.status is BranchDeletionStatus.DELETED
    assert safety.links_for_node(root_id) == ()
    assert safety.links_for_node(child_id) == ()

    preview = state.undo_preview()
    assert preview is not None
    assert transactions.deletion_history_subject(preview.metadata) == root_id
    assert transactions.deletion_history_removed_ids(preview.metadata) == (
        root_id,
        child_id,
    )

    restored_ids = transactions.restore_deletion_history(preview.metadata)
    assert restored_ids == (root_id, child_id)
    transition = state.undo_only()
    assert transition is not None
    assert state.custom_subtree_ids(root_id) == (root_id, child_id)
    assert safety.links_for_node(root_id) == normalized_links
    assert safety.links_for_node(child_id) == normalized_links
    connection.close()


def test_guarded_redo_preserves_older_redo_entries_and_layout(tmp_path) -> None:
    database_path = tmp_path / "runtime-redo.sqlite3"
    connection = _connect(database_path)
    create_minimal_schema(connection)
    operations = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(connection)
    )
    safety = LineageRuntimeSafety(
        SQLiteLineageResourceLinksRepository(connection),
        operations,
    )
    transactions = LineageBranchTransactions(safety)
    state = AtomicLineageStateStore(tmp_path / "lineage-redo.json")
    branch_id = state.continue_from("snapshot")
    links = (ResourceClaim("model_version", "mdl_redo", "read"),)
    safety.bind_node(branch_id, links)
    controller = BranchDeletionController(state, transactions)
    plan = controller.prepare(
        branch_id,
        node_title="Branch",
        parent_id="snapshot",
        graph_current_id="snapshot",
    )
    assert plan is not None
    assert controller.execute(plan).status is BranchDeletionStatus.DELETED

    state.record_layout_action(
        "layout_reset_all",
        {"schema": 1, "phase": "before-layout"},
    )
    layout_undo = state.undo_only(
        {"schema": 1, "phase": "after-layout"}
    )
    assert layout_undo is not None
    assert layout_undo.action_code == "layout_reset_all"

    delete_preview = state.undo_preview()
    assert delete_preview is not None
    assert delete_preview.action_code == "branch_delete"
    transactions.restore_deletion_history(delete_preview.metadata)
    delete_undo = state.undo_only(
        {"schema": 1, "phase": "deleted-layout"}
    )
    assert delete_undo is not None
    assert state.is_custom_node(branch_id) is True

    redo_plan = controller.prepare(
        branch_id,
        node_title="Branch",
        parent_id="snapshot",
        graph_current_id="snapshot",
    )
    assert redo_plan is not None
    result = controller.execute_history_redo(
        redo_plan,
        current_layout={"schema": 1, "phase": "restored-layout"},
    )

    assert result.status is BranchDeletionStatus.DELETED
    assert result.history_transition is not None
    assert result.history_transition.action_code == "branch_delete"
    assert result.history_transition.direction == "redo"
    assert result.history_transition.layout_snapshot == {
        "schema": 1,
        "phase": "deleted-layout",
    }
    assert state.is_custom_node(branch_id) is False
    assert safety.links_for_node(branch_id) == ()
    payload = state.capture_transaction_state()
    assert [entry["action_code"] for entry in payload["redo_stack"]] == [
        "layout_reset_all"
    ]
    assert payload["undo_stack"][-1]["action_code"] == "branch_delete"
    connection.close()


def test_guarded_redo_stays_pending_when_runtime_resource_is_active(
    tmp_path,
) -> None:
    database_path = tmp_path / "runtime-redo-blocked.sqlite3"
    connection = _connect(database_path)
    create_minimal_schema(connection)
    operations = RuntimeOperationCoordinator(
        SQLiteRuntimeOperationsRepository(connection)
    )
    safety = LineageRuntimeSafety(
        SQLiteLineageResourceLinksRepository(connection),
        operations,
    )
    transactions = LineageBranchTransactions(safety)
    state = AtomicLineageStateStore(tmp_path / "lineage-redo-blocked.json")
    branch_id = state.continue_from("snapshot")
    links = (ResourceClaim("model_version", "mdl_guard", "read"),)
    safety.bind_node(branch_id, links)
    controller = BranchDeletionController(state, transactions)
    plan = controller.prepare(
        branch_id,
        node_title="Branch",
        parent_id="snapshot",
        graph_current_id="snapshot",
    )
    assert plan is not None
    assert controller.execute(plan).status is BranchDeletionStatus.DELETED

    preview = state.undo_preview()
    assert preview is not None
    transactions.restore_deletion_history(preview.metadata)
    assert state.undo_only() is not None
    assert state.is_custom_node(branch_id) is True
    normalized_links = safety.links_for_node(branch_id)

    training = operations.begin(
        operation_kind="training",
        subject_kind="training_run",
        subject_id="trn_guard",
        claims=(ResourceClaim("model_version", "mdl_guard", "read"),),
    )
    redo_plan = controller.prepare(
        branch_id,
        node_title="Branch",
        parent_id="snapshot",
        graph_current_id="snapshot",
    )
    assert redo_plan is not None
    result = controller.execute_history_redo(redo_plan)

    assert result.status is BranchDeletionStatus.BLOCKED
    assert result.blockers
    assert state.is_custom_node(branch_id) is True
    assert safety.links_for_node(branch_id) == normalized_links
    pending = state.history_toggle_preview()
    assert pending is not None
    assert pending.action_code == "branch_delete"
    assert pending.direction == "redo"
    assert training.succeed() is True
    connection.close()


class _RedoController:
    def __init__(self, result: BranchDeletionResult) -> None:
        self.result = result
        self.executed: list[BranchDeletionPlan] = []

    def prepare(self, *args, **kwargs) -> BranchDeletionPlan:
        return BranchDeletionPlan(
            node_id="branch_001",
            node_title="Branch",
            removed_ids=("branch_001", "branch_002"),
            fallback_id="snapshot",
        )

    def execute_history_redo(
        self,
        plan,
        *,
        current_layout=None,
    ) -> BranchDeletionResult:
        self.executed.append(plan)
        return self.result


class _HistoryTransactions:
    def __init__(self) -> None:
        self.restored: list[dict[str, object]] = []
        self.forgotten: list[tuple[str, ...]] = []

    def deletion_history_subject(self, metadata) -> str:
        return str(metadata.get("subject_node_id", ""))

    def deletion_history_removed_ids(self, metadata) -> tuple[str, ...]:
        return tuple(metadata.get("removed_ids", ()))

    def restore_deletion_history(self, metadata) -> tuple[str, ...]:
        self.restored.append(dict(metadata))
        return tuple(metadata.get("removed_ids", ()))

    def forget(self, node_ids) -> int:
        values = tuple(node_ids)
        self.forgotten.append(values)
        return len(values)


def test_agents_redo_delete_reuses_guarded_deletion_controller() -> None:
    blocker = SimpleNamespace(message="training holds model")
    result = BranchDeletionResult(
        BranchDeletionStatus.BLOCKED,
        blockers=(blocker,),  # type: ignore[arg-type]
    )
    controller = _RedoController(result)
    transactions = _HistoryTransactions()
    preview = SimpleNamespace(
        action_code="branch_delete",
        direction="redo",
        metadata={
            "subject_node_id": "branch_001",
            "removed_ids": ["branch_001", "branch_002"],
        },
    )
    blockers: list[object] = []
    state = SimpleNamespace(
        history_toggle_preview=lambda: preview,
        is_custom_node=lambda node_id: node_id == "branch_001",
        quick_toggle=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("generic history redo must not run")
        ),
    )
    screen = SimpleNamespace(
        _state=state,
        _branch_transactions=transactions,
        _branch_deletion_controller=controller,
        _close_canvas_menu=lambda: None,
        _node_by_id=lambda _node_id: SimpleNamespace(
            title="Branch",
            parent_id="snapshot",
        ),
        _render_text=lambda value: value,
        _graph=SimpleNamespace(current_node_id=lambda: "snapshot"),
        _layout_snapshot=lambda: {"schema": 1},
        _show_runtime_blockers=lambda values: blockers.extend(values),
        _apply_branch_deletion_result=lambda _result: None,
        _refresh_lineage=lambda *, center: None,
        _sync_history_action=lambda: None,
    )
    screen._redo_branch_delete_history = lambda value: (  # type: ignore[attr-defined]
        WorkspaceCompositionAgentsScreen._redo_branch_delete_history(
            screen,  # type: ignore[arg-type]
            value,
        )
    )

    WorkspaceCompositionAgentsScreen._toggle_last_history_action(  # type: ignore[arg-type]
        screen
    )

    assert len(controller.executed) == 1
    assert blockers == [blocker]


def test_agents_undo_delete_restores_links_before_lineage_state() -> None:
    order: list[str] = []
    metadata = {
        "subject_node_id": "branch_001",
        "removed_ids": ["branch_001"],
    }
    preview = SimpleNamespace(
        action_code="branch_delete",
        direction="undo",
        metadata=metadata,
    )
    transition = HistoryTransition(
        action_code="branch_delete",
        direction="undo",
        layout_snapshot={"schema": 1},
        critical=True,
    )
    transactions = _HistoryTransactions()
    restore_base = transactions.restore_deletion_history

    def restore(values):
        order.append("links")
        return restore_base(values)

    transactions.restore_deletion_history = restore  # type: ignore[method-assign]
    state = SimpleNamespace(
        undo_preview=lambda: preview,
        undo_only=lambda _layout: (order.append("state") or transition),
    )
    applied: list[HistoryTransition] = []
    screen = SimpleNamespace(
        _state=state,
        _branch_transactions=transactions,
        _close_canvas_menu=lambda: None,
        _layout_snapshot=lambda: {"schema": 1},
        _apply_history_transition=applied.append,
        _refresh_runtime_safety=lambda *, force: order.append("refresh"),
        _sync_history_action=lambda: None,
    )
    screen._undo_branch_delete_history = lambda value: (  # type: ignore[attr-defined]
        WorkspaceCompositionAgentsScreen._undo_branch_delete_history(
            screen,  # type: ignore[arg-type]
            value,
        )
    )

    WorkspaceCompositionAgentsScreen._undo_history_only(  # type: ignore[arg-type]
        screen
    )

    assert order[:2] == ["links", "state"]
    assert applied == [transition]
    assert order[-1] == "refresh"


def test_agents_redo_delete_applies_saved_layout_transition() -> None:
    transition = HistoryTransition(
        action_code="branch_delete",
        direction="redo",
        layout_snapshot={"schema": 1, "phase": "deleted"},
        critical=True,
    )
    result = BranchDeletionResult(
        BranchDeletionStatus.DELETED,
        removed_ids=("branch_001",),
        fallback_id="snapshot",
        history_transition=transition,
    )
    forgotten: list[tuple[str, ...]] = []
    applied: list[HistoryTransition] = []
    refreshed: list[bool] = []
    screen = SimpleNamespace(
        _graph=SimpleNamespace(
            forget_layout_nodes=lambda node_ids: forgotten.append(
                tuple(node_ids)
            )
        ),
        _apply_history_transition=applied.append,
        _refresh_runtime_safety=lambda *, force: refreshed.append(force),
        _apply_branch_deletion_result=lambda _result: (_ for _ in ()).throw(
            AssertionError("guarded redo must apply its history transition")
        ),
    )

    WorkspaceCompositionAgentsScreen._apply_branch_delete_history_redo_result(  # type: ignore[arg-type]
        screen,
        result,
    )

    assert forgotten == [("branch_001",)]
    assert applied == [transition]
    assert refreshed == [True]

from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.runtime_policy import (
    LineageBranchTransactions,
    LineageRuntimePolicy,
)


def test_runtime_policy_prefers_persisted_links_for_custom_nodes() -> None:
    linked = (ResourceClaim("model_version", "mdl_custom", "read"),)
    safety = SimpleNamespace(links_for_node=lambda _node_id: linked)
    policy = LineageRuntimePolicy(safety)  # type: ignore[arg-type]
    projection = {
        "branch_001": (
            ResourceClaim("model_version", "mdl_projection", "read"),
        )
    }

    assert policy.claims_for_node(
        "branch_001",
        is_custom=True,
        projection_resources=projection,
    ) == linked
    assert policy.claims_for_node(
        "branch_001",
        is_custom=False,
        projection_resources=projection,
    ) == projection["branch_001"]


def test_runtime_policy_builds_stable_blocker_state() -> None:
    blockers = (
        SimpleNamespace(
            operation=SimpleNamespace(
                operation_id="op_2",
                operation_kind="portrait",
                subject_id="evr_2",
            ),
            claim=ResourceClaim("model_version", "mdl_2", "write"),
        ),
        SimpleNamespace(
            operation=SimpleNamespace(
                operation_id="op_1",
                operation_kind="training",
                subject_id="trn_1",
            ),
            claim=ResourceClaim("artifact_path", "/artifacts/1", "write"),
        ),
    )
    safety = SimpleNamespace(
        deletion_blockers=lambda _node_ids: blockers,
        blocker_text=lambda _blockers: "stable blocker text",
    )
    state = LineageRuntimePolicy(safety).blockers_for(  # type: ignore[arg-type]
        ("branch_001",)
    )

    assert state.blockers == blockers
    assert state.signature == (
        ("op_1", "artifact_path", "/artifacts/1"),
        ("op_2", "model_version", "mdl_2"),
    )
    assert state.text == "stable blocker text"


def test_runtime_policy_returns_semantic_action_overrides() -> None:
    policy = LineageRuntimePolicy(None)

    registered = policy.action_overrides(
        node_kind="model_version",
        is_custom=False,
        is_current=False,
        is_archived=False,
    )
    assert registered.make_current is True
    assert registered.compare is True
    assert registered.portrait is True
    assert registered.branch is True
    assert registered.delete is False
    assert registered.delete_reason_code == "registered_model_version"

    current_archived = policy.action_overrides(
        node_kind="model_version",
        is_custom=False,
        is_current=True,
        is_archived=True,
    )
    assert current_archived.make_current is False
    assert current_archived.compare is False
    assert current_archived.branch is False


def test_runtime_policy_blocks_custom_delete_without_ui_text_protocol() -> None:
    blocker = SimpleNamespace(
        operation=SimpleNamespace(
            operation_id="op_1",
            operation_kind="portrait",
            subject_id="evr_1",
        ),
        claim=ResourceClaim("model_version", "mdl_1", "write"),
    )
    safety = SimpleNamespace(
        deletion_blockers=lambda _node_ids: (blocker,),
        blocker_text=lambda _blockers: "portrait · evr_1",
    )
    override = LineageRuntimePolicy(safety).action_overrides(  # type: ignore[arg-type]
        node_kind="custom_branch",
        is_custom=True,
        is_current=False,
        is_archived=False,
        subtree_ids=("branch_001",),
    )

    assert override.delete is False
    assert override.delete_reason_code == "active_operation"
    assert override.blocker_text == "portrait · evr_1"


def test_branch_transactions_choose_inherit_or_bind_explicitly() -> None:
    calls: list[tuple[object, ...]] = []

    class _Safety:
        def inherit_node(self, child, parent, *, fallback_claims=()):
            calls.append(("inherit", child, parent, tuple(fallback_claims)))
            return tuple(fallback_claims)

        def bind_node(self, child, claims):
            calls.append(("bind", child, tuple(claims)))
            return tuple(claims)

        def begin_deletion(self, node_ids, *, subject_id):
            calls.append(("delete", tuple(node_ids), subject_id))
            return "lease"

        def forget_nodes(self, node_ids):
            calls.append(("forget", tuple(node_ids)))
            return len(tuple(node_ids))

    transactions = LineageBranchTransactions(_Safety())  # type: ignore[arg-type]
    claims = (ResourceClaim("model_version", "mdl_1", "read"),)

    assert transactions.bind_child(
        "branch_002",
        "branch_001",
        parent_is_custom=True,
        fallback_claims=claims,
    ) == claims
    assert transactions.bind_child(
        "branch_003",
        "snapshot",
        parent_is_custom=False,
        fallback_claims=claims,
    ) == claims
    assert transactions.begin_deletion(
        ("branch_002", "branch_003"),
        subject_id="branch_002",
    ) == "lease"
    assert transactions.forget(("branch_002", "branch_003")) == 2
    assert calls == [
        ("inherit", "branch_002", "branch_001", claims),
        ("bind", "branch_003", claims),
        ("delete", ("branch_002", "branch_003"), "branch_002"),
        ("forget", ("branch_002", "branch_003")),
    ]

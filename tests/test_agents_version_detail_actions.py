from __future__ import annotations

from persona_training_lab.ui.agents.screen_agents_final import AgentsScreen


def test_current_snapshot_keeps_safe_actions_only() -> None:
    capabilities = AgentsScreen._detail_capabilities(
        "snapshot",
        is_custom=False,
        is_current=True,
        is_archived=False,
    )

    assert capabilities == {
        "make_current": False,
        "compare": False,
        "portrait": True,
        "branch": True,
        "delete": False,
    }


def test_local_branch_can_be_promoted_compared_and_deleted() -> None:
    capabilities = AgentsScreen._detail_capabilities(
        "branch_17",
        is_custom=True,
        is_current=False,
        is_archived=False,
    )

    assert capabilities == {
        "make_current": True,
        "compare": True,
        "portrait": True,
        "branch": True,
        "delete": True,
    }


def test_archived_branch_cannot_be_promoted_or_continued() -> None:
    capabilities = AgentsScreen._detail_capabilities(
        "branch_archived",
        is_custom=True,
        is_current=False,
        is_archived=True,
    )

    assert capabilities["make_current"] is False
    assert capabilities["branch"] is False
    assert capabilities["compare"] is True
    assert capabilities["portrait"] is True
    assert capabilities["delete"] is True


def test_non_version_lineage_node_does_not_offer_version_operations() -> None:
    capabilities = AgentsScreen._detail_capabilities(
        "training",
        is_custom=False,
        is_current=False,
        is_archived=False,
    )

    assert capabilities["make_current"] is False
    assert capabilities["compare"] is False
    assert capabilities["portrait"] is False
    assert capabilities["delete"] is False
    assert capabilities["branch"] is True

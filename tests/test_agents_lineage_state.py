from __future__ import annotations

import json

from persona_training_lab.ui.agents.lineage import LineageVersionNode
from persona_training_lab.ui.agents.lineage_state import (
    CRITICAL_HISTORY_RESERVE,
    RECENT_HISTORY_LIMIT,
    TOTAL_HISTORY_LIMIT,
    LineageStateStore,
)


def _base_nodes() -> tuple[LineageVersionNode, ...]:
    return (
        LineageVersionNode("base", None, "Base", "root", "source", "good", "main", level=0),
        LineageVersionNode("snapshot", "base", "Version", "snapshot", "ready", "good", "current", is_current=True, level=1),
    )


def test_lineage_state_marks_current_and_tone(tmp_path) -> None:
    store = LineageStateStore(tmp_path / "state.json")
    store.set_tone("base", "bad")
    store.set_current("base")
    lineage = {node.node_id: node for node in store.apply(_base_nodes())}
    assert lineage["base"].tone == "bad"
    assert lineage["base"].status == "неудачная"
    assert lineage["base"].is_current is True
    assert lineage["snapshot"].is_current is False
    assert lineage["snapshot"].branch_note == "main"


def test_lineage_state_creates_persistent_child_branch(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    branch_id = store.continue_from("snapshot")
    lineage = {node.node_id: node for node in store.apply(_base_nodes())}
    assert branch_id in lineage
    assert lineage[branch_id].parent_id == "snapshot"
    assert lineage[branch_id].tone == "pending"
    assert lineage[branch_id].branch_note == "side"
    assert lineage[branch_id].level == lineage["snapshot"].level + 1
    assert branch_id in {node.node_id for node in LineageStateStore(path).apply(_base_nodes())}


def test_custom_branch_accepts_tone_overrides(tmp_path) -> None:
    store = LineageStateStore(tmp_path / "state.json")
    branch_id = store.continue_from("snapshot")
    store.set_tone(branch_id, "bad")
    bad_lineage = {node.node_id: node for node in store.apply(_base_nodes())}
    assert bad_lineage[branch_id].tone == "bad"
    assert bad_lineage[branch_id].status == "неудачная"
    store.set_tone(branch_id, "good")
    good_lineage = {node.node_id: node for node in store.apply(_base_nodes())}
    assert good_lineage[branch_id].tone == "good"
    assert good_lineage[branch_id].status == "удачная"
    store.set_tone(branch_id, "pending")
    pending_lineage = {node.node_id: node for node in store.apply(_base_nodes())}
    assert pending_lineage[branch_id].tone == "pending"
    assert pending_lineage[branch_id].status == "спорная"


def test_custom_branch_can_be_renamed_and_archived_without_losing_tone(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    branch_id = store.continue_from("snapshot")
    store.set_tone(branch_id, "good")
    assert store.rename_node(branch_id, "  stable experiment  ") is True
    assert store.set_archived(branch_id, True) is True
    archived = {node.node_id: node for node in store.apply(_base_nodes())}
    assert archived[branch_id].title == "stable experiment"
    assert archived[branch_id].status == "архивная"
    assert archived[branch_id].tone == "neutral"
    assert store.set_archived(branch_id, False) is True
    restored = {node.node_id: node for node in LineageStateStore(path).apply(_base_nodes())}
    assert restored[branch_id].status == "удачная"
    assert restored[branch_id].tone == "good"


def test_archiving_branch_archives_entire_subtree_and_restores_each_tone(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    root_id = store.continue_from("snapshot")
    child_id = store.continue_from(root_id)
    grandchild_id = store.continue_from(child_id)
    sibling_id = store.continue_from("snapshot")
    store.set_tone(root_id, "good")
    store.set_tone(child_id, "bad")
    store.set_tone(grandchild_id, "pending")
    store.set_tone(sibling_id, "good")
    assert store.set_archived(root_id, True) is True
    archived = {node.node_id: node for node in store.apply(_base_nodes())}
    for node_id in (root_id, child_id, grandchild_id):
        assert archived[node_id].status == "архивная"
        assert archived[node_id].tone == "neutral"
    assert archived[sibling_id].status == "удачная"
    assert archived[sibling_id].tone == "good"
    assert store.set_archived(root_id, False) is True
    restored = {node.node_id: node for node in LineageStateStore(path).apply(_base_nodes())}
    assert (restored[root_id].status, restored[root_id].tone) == ("удачная", "good")
    assert (restored[child_id].status, restored[child_id].tone) == ("неудачная", "bad")
    assert (restored[grandchild_id].status, restored[grandchild_id].tone) == ("спорная", "pending")


def test_delete_custom_subtree_removes_descendants_and_restores_current_parent(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    root_id = store.continue_from("snapshot")
    child_id = store.continue_from(root_id)
    grandchild_id = store.continue_from(child_id)
    sibling_id = store.continue_from("snapshot")
    store.set_current(grandchild_id)
    removed = store.delete_subtree(root_id)
    lineage = {node.node_id: node for node in store.apply(_base_nodes())}
    assert removed == (root_id, child_id, grandchild_id)
    assert root_id not in lineage
    assert child_id not in lineage
    assert grandchild_id not in lineage
    assert sibling_id in lineage
    assert store.current_node_id() == "snapshot"


def test_undo_creation_removes_created_branch_and_persists(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    branch_id = store.continue_from("snapshot")
    assert store.can_undo() is True
    assert store.last_action_label() == "создание ветки"
    assert store.undo_last_action() == "создание ветки"
    reloaded = LineageStateStore(path)
    assert branch_id not in {node.node_id for node in reloaded.apply(_base_nodes())}
    assert reloaded.can_undo() is False
    assert reloaded.can_redo() is True


def test_undo_archive_restores_complete_subtree_tones(tmp_path) -> None:
    store = LineageStateStore(tmp_path / "state.json")
    root_id = store.continue_from("snapshot")
    child_id = store.continue_from(root_id)
    store.set_tone(root_id, "good")
    store.set_tone(child_id, "bad")
    store.set_archived(root_id, True)
    assert store.undo_last_action() == "архивация ветки"
    restored = {node.node_id: node for node in store.apply(_base_nodes())}
    assert (restored[root_id].status, restored[root_id].tone) == ("удачная", "good")
    assert (restored[child_id].status, restored[child_id].tone) == ("неудачная", "bad")


def test_undo_delete_restores_subtree_and_current_version(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    root_id = store.continue_from("snapshot")
    child_id = store.continue_from(root_id)
    store.set_current(child_id)
    store.delete_subtree(root_id)
    assert store.current_node_id() == "snapshot"
    assert store.undo_last_action() == "удаление ветки"
    restored_store = LineageStateStore(path)
    restored = {node.node_id: node for node in restored_store.apply(_base_nodes())}
    assert root_id in restored
    assert child_id in restored
    assert restored_store.current_node_id() == child_id


def test_quick_toggle_alternates_undo_and_redo_without_growing_history(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    before_layout = {"schema": 1, "offsets": {}}
    after_layout = {"schema": 1, "offsets": {"branch_001": {"x": 12.0, "y": 8.0}}}
    branch_id = store.continue_from("snapshot", before_layout)

    for index in range(10):
        current_layout = after_layout if index % 2 == 0 else before_layout
        transition = store.quick_toggle(current_layout)
        assert transition is not None
        if index % 2 == 0:
            assert transition.direction == "undo"
            assert transition.layout_snapshot == before_layout
            assert branch_id not in {node.node_id for node in store.apply(_base_nodes())}
        else:
            assert transition.direction == "redo"
            assert transition.layout_snapshot == after_layout
            assert branch_id in {node.node_id for node in store.apply(_base_nodes())}

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["undo_stack"]) + len(payload["redo_stack"]) == 1


def test_undo_only_walks_back_instead_of_toggling_forward(tmp_path) -> None:
    store = LineageStateStore(tmp_path / "state.json")
    branch_id = store.continue_from("snapshot")
    store.rename_node(branch_id, "renamed")
    store.set_tone(branch_id, "good")

    assert store.undo_only().label == "изменение статуса"
    assert store.undo_only().label == "переименование ветки"
    assert store.undo_only().label == "создание ветки"
    assert branch_id not in {node.node_id for node in store.apply(_base_nodes())}


def test_layout_history_round_trips_before_and_after_snapshots(tmp_path) -> None:
    store = LineageStateStore(tmp_path / "state.json")
    before = {"schema": 1, "offsets": {}}
    after = {"schema": 1, "offsets": {"snapshot": {"x": 25.0, "y": -4.0}}}
    store.record_layout_action("перемещение точки", before)

    undone = store.quick_toggle(after)
    assert undone is not None
    assert undone.direction == "undo"
    assert undone.layout_snapshot == before

    redone = store.quick_toggle(before)
    assert redone is not None
    assert redone.direction == "redo"
    assert redone.layout_snapshot == after


def test_history_keeps_fifty_recent_actions_plus_twenty_older_critical_actions(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    empty_layout = {"schema": 1, "offsets": {}}

    for index in range(25):
        store.record_layout_action(f"critical {index}", empty_layout, critical=True)
    for index in range(80):
        store.record_layout_action(f"noise {index}", empty_layout)

    payload = json.loads(path.read_text(encoding="utf-8"))
    stack = payload["undo_stack"]
    assert len(stack) == TOTAL_HISTORY_LIMIT
    protected = stack[:-RECENT_HISTORY_LIMIT]
    recent = stack[-RECENT_HISTORY_LIMIT:]
    assert len(protected) == CRITICAL_HISTORY_RESERVE
    assert all(entry["critical"] is True for entry in protected)
    assert [entry["label"] for entry in protected] == [f"critical {index}" for index in range(5, 25)]
    assert [entry["label"] for entry in recent] == [f"noise {index}" for index in range(30, 80)]


def test_branch_deletion_is_marked_critical(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    branch_id = store.continue_from("snapshot")
    store.delete_subtree(branch_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["undo_stack"][-1]["label"] == "удаление ветки"
    assert payload["undo_stack"][-1]["critical"] is True


def test_base_nodes_are_protected_from_destructive_branch_actions(tmp_path) -> None:
    store = LineageStateStore(tmp_path / "state.json")
    assert store.rename_node("snapshot", "renamed") is False
    assert store.set_archived("snapshot", True) is False
    assert store.delete_subtree("snapshot") == ()

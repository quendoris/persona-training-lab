from __future__ import annotations

from persona_training_lab.ui.agents.lineage import LineageVersionNode
from persona_training_lab.ui.agents.lineage_state import LineageStateStore


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


def test_base_nodes_are_protected_from_destructive_branch_actions(tmp_path) -> None:
    store = LineageStateStore(tmp_path / "state.json")
    assert store.rename_node("snapshot", "renamed") is False
    assert store.set_archived("snapshot", True) is False
    assert store.delete_subtree("snapshot") == ()

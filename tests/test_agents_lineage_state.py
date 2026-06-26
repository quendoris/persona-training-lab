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

    reloaded = LineageStateStore(path)
    reloaded_lineage = {node.node_id: node for node in reloaded.apply(_base_nodes())}
    assert branch_id in reloaded_lineage

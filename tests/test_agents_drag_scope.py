from __future__ import annotations

from persona_training_lab.ui.agents.drag_scope import drag_history_label, drag_target_ids


def test_drag_scope_switches_node_subtree_node_without_releasing_mouse() -> None:
    subtree = ("branch_001", "branch_002", "branch_003")

    assert drag_target_ids("branch_001", subtree, shift_down=False) == ("branch_001",)
    assert drag_target_ids("branch_001", subtree, shift_down=True) == subtree
    assert drag_target_ids("branch_001", subtree, shift_down=False) == ("branch_001",)


def test_mixed_drag_is_recorded_as_one_combined_history_action() -> None:
    assert drag_history_label(moved_node=True, moved_subtree=True) == "перемещение точки и поддерева"
    assert drag_history_label(moved_node=False, moved_subtree=True) == "перемещение поддерева"
    assert drag_history_label(moved_node=True, moved_subtree=False) == "перемещение точки"

from __future__ import annotations

import json

from persona_training_lab.ui.keybindings.draft_session import (
    KeyBindingDraftSession,
)
from persona_training_lab.ui.keybindings.manager import (
    KeyBindingManager,
    MouseBindingValue,
)


def test_keyboard_conflict_stays_draft_until_resolved(tmp_path) -> None:
    path = tmp_path / "key_bindings.json"
    manager = KeyBindingManager(storage_path=path)
    draft = KeyBindingDraftSession(manager)

    conflict = draft.set_sequence("delete_branch", "Ctrl+Z")

    assert conflict.accepted is True
    assert conflict.changed is True
    assert draft.has_conflicts is True
    assert set(draft.keyboard_conflicts()) == {
        "delete_branch",
        "history_toggle",
    }
    assert draft.sequence("delete_branch") == "Ctrl+Z"
    assert manager.sequence("delete_branch") == "Del"
    assert path.exists() is False

    resolved = draft.set_sequence("history_toggle", "Ctrl+Y")

    assert resolved.accepted is True
    assert draft.has_conflicts is False
    assert draft.is_dirty is False
    assert manager.sequence("delete_branch") == "Ctrl+Z"
    assert manager.sequence("history_toggle") == "Ctrl+Y"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["bindings"]["delete_branch"] == "Ctrl+Z"
    assert payload["bindings"]["history_toggle"] == "Ctrl+Y"


def test_keyboard_swap_commits_without_intermediate_active_conflict(
    tmp_path,
) -> None:
    path = tmp_path / "key_bindings.json"
    manager = KeyBindingManager(storage_path=path)
    draft = KeyBindingDraftSession(manager)

    draft.set_sequence("delete_branch", "Ctrl+Z")
    assert draft.has_conflicts is True
    assert manager.sequence("delete_branch") == "Del"

    result = draft.set_sequence("history_toggle", "Del")

    assert result.accepted is True
    assert draft.has_conflicts is False
    assert manager.sequence("delete_branch") == "Ctrl+Z"
    assert manager.sequence("history_toggle") == "Del"


def test_mouse_conflict_uses_draft_and_commits_atomically(tmp_path) -> None:
    path = tmp_path / "key_bindings.json"
    manager = KeyBindingManager(storage_path=path)
    draft = KeyBindingDraftSession(manager)

    conflict = draft.set_mouse_binding("move_node", "left", "none")

    assert conflict.accepted is True
    assert draft.has_conflicts is True
    assert set(draft.mouse_conflicts()) == {
        "move_node",
        "open_node_menu",
    }
    assert draft.mouse_binding("move_node") == MouseBindingValue(
        "left",
        "none",
    )
    assert manager.mouse_binding("move_node") == MouseBindingValue(
        "right",
        "none",
    )

    resolved = draft.set_mouse_binding(
        "open_node_menu",
        "middle",
        "none",
    )

    assert resolved.accepted is True
    assert draft.has_conflicts is False
    assert manager.mouse_binding("move_node") == MouseBindingValue(
        "left",
        "none",
    )
    assert manager.mouse_binding("open_node_menu") == MouseBindingValue(
        "middle",
        "none",
    )


def test_discard_conflicting_changes_restores_active_bindings(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    draft = KeyBindingDraftSession(manager)

    draft.set_sequence("delete_branch", "Ctrl+Z")
    assert draft.has_conflicts is True

    result = draft.discard_conflicting_changes()

    assert result.accepted is True
    assert draft.has_conflicts is False
    assert draft.is_dirty is False
    assert draft.sequence("delete_branch") == "Del"
    assert draft.sequence("history_toggle") == "Ctrl+Z"

from __future__ import annotations

import json

from persona_training_lab.ui.keybindings.manager import (
    KeyBindingManager,
    MouseBindingValue,
)


def test_key_binding_manager_uses_stable_defaults(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")

    assert manager.sequence("delete_branch") == "Del"
    assert manager.sequence("history_toggle") == "Ctrl+Z"
    assert manager.sequence("undo_only") == "Ctrl+Shift+Z"
    assert {item.binding_id for item in manager.definitions()} == {
        "delete_branch",
        "history_toggle",
        "undo_only",
    }
    assert manager.mouse_binding("open_node_menu") == MouseBindingValue(
        "left",
        "none",
    )
    assert manager.mouse_binding("move_node") == MouseBindingValue(
        "right",
        "none",
    )
    assert manager.mouse_binding("move_subtree") == MouseBindingValue(
        "right",
        "shift",
    )
    assert manager.mouse_binding("zoom_canvas") == MouseBindingValue(
        "wheel",
        "none",
    )


def test_key_binding_change_is_persisted_and_emitted(tmp_path) -> None:
    path = tmp_path / "key_bindings.json"
    manager = KeyBindingManager(storage_path=path)
    emissions: list[dict[str, str]] = []
    manager.bindings_changed.connect(
        lambda: emissions.append(manager.current_bindings())
    )

    result = manager.set_sequence("history_toggle", "Ctrl+Y")

    assert result.accepted is True
    assert result.changed is True
    assert manager.sequence("history_toggle") == "Ctrl+Y"
    assert len(emissions) == 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 2
    assert payload["bindings"]["history_toggle"] == "Ctrl+Y"
    assert payload["mouse_bindings"]["move_node"] == {
        "button": "right",
        "modifier": "none",
    }

    restored = KeyBindingManager(storage_path=path)
    assert restored.sequence("history_toggle") == "Ctrl+Y"


def test_mouse_binding_change_is_persisted_and_emitted(tmp_path) -> None:
    path = tmp_path / "key_bindings.json"
    manager = KeyBindingManager(storage_path=path)
    emissions: list[dict[str, MouseBindingValue]] = []
    manager.bindings_changed.connect(
        lambda: emissions.append(manager.current_mouse_bindings())
    )

    result = manager.set_mouse_binding(
        "pan_canvas_secondary",
        "middle",
        "alt",
    )

    assert result.accepted is True
    assert result.changed is True
    assert manager.mouse_binding("pan_canvas_secondary") == MouseBindingValue(
        "middle",
        "alt",
    )
    assert manager.mouse_binding_text("pan_canvas_secondary") == (
        "Alt + Средняя кнопка"
    )
    assert len(emissions) == 1

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["mouse_bindings"]["pan_canvas_secondary"] == {
        "button": "middle",
        "modifier": "alt",
    }
    restored = KeyBindingManager(storage_path=path)
    assert restored.mouse_binding("pan_canvas_secondary") == MouseBindingValue(
        "middle",
        "alt",
    )


def test_key_binding_manager_rejects_conflicts_without_writing(tmp_path) -> None:
    path = tmp_path / "key_bindings.json"
    manager = KeyBindingManager(storage_path=path)

    result = manager.set_sequence("delete_branch", "Ctrl+Z")

    assert result.accepted is False
    assert result.changed is False
    assert result.conflict_binding_id == "history_toggle"
    assert "Отменить или вернуть" in result.conflict_title
    assert manager.sequence("delete_branch") == "Del"
    assert path.exists() is False


def test_mouse_node_click_and_drag_reject_ambiguous_same_gesture(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")

    result = manager.set_mouse_binding("move_node", "left", "none")

    assert result.accepted is False
    assert result.conflict_binding_id == "open_node_menu"
    assert result.conflict_title == "Открыть действия узла"
    assert manager.mouse_binding("move_node") == MouseBindingValue(
        "right",
        "none",
    )


def test_canvas_click_and_drag_may_share_one_button(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")

    assert manager.set_mouse_binding(
        "pan_canvas_primary",
        "middle",
        "none",
    ).accepted
    result = manager.set_mouse_binding(
        "close_node_menu",
        "middle",
        "none",
    )

    assert result.accepted is True
    assert manager.mouse_binding("close_node_menu") == MouseBindingValue(
        "middle",
        "none",
    )


def test_wheel_action_keeps_wheel_but_allows_modifier_change(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")

    rejected = manager.set_mouse_binding("zoom_canvas", "middle", "control")
    accepted = manager.set_mouse_binding("zoom_canvas", "wheel", "control")

    assert rejected.accepted is False
    assert "колесе мыши" in rejected.error
    assert accepted.accepted is True
    assert manager.mouse_binding("zoom_canvas") == MouseBindingValue(
        "wheel",
        "control",
    )


def test_reset_binding_and_reset_all_restore_defaults(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    assert manager.set_sequence("history_toggle", "Ctrl+Y").accepted
    assert manager.set_sequence("undo_only", "Ctrl+Shift+Y").accepted
    assert manager.set_mouse_binding(
        "pan_canvas_secondary",
        "middle",
        "alt",
    ).accepted

    one = manager.reset_binding("history_toggle")
    mouse_one = manager.reset_mouse_binding("pan_canvas_secondary")
    assert one.accepted is True
    assert mouse_one.accepted is True
    assert manager.sequence("history_toggle") == "Ctrl+Z"
    assert manager.sequence("undo_only") == "Ctrl+Shift+Y"
    assert manager.mouse_binding("pan_canvas_secondary") == MouseBindingValue(
        "right",
        "none",
    )

    assert manager.set_mouse_binding(
        "zoom_canvas",
        "wheel",
        "control",
    ).accepted
    all_result = manager.reset_all()
    assert all_result.accepted is True
    assert manager.sequence("history_toggle") == "Ctrl+Z"
    assert manager.sequence("undo_only") == "Ctrl+Shift+Z"
    assert manager.mouse_binding("zoom_canvas") == MouseBindingValue(
        "wheel",
        "none",
    )


def test_version_one_file_migrates_keyboard_and_uses_mouse_defaults(
    tmp_path,
) -> None:
    path = tmp_path / "key_bindings.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "bindings": {
                    "delete_branch": "Del",
                    "history_toggle": "Ctrl+Y",
                    "undo_only": "Ctrl+Shift+Y",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = KeyBindingManager(storage_path=path)

    assert manager.sequence("history_toggle") == "Ctrl+Y"
    assert manager.sequence("undo_only") == "Ctrl+Shift+Y"
    assert manager.mouse_binding("move_node") == MouseBindingValue(
        "right",
        "none",
    )
    assert manager.last_error == ""


def test_corrupted_file_falls_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "key_bindings.json"
    path.write_text("{not-json", encoding="utf-8")

    manager = KeyBindingManager(storage_path=path)

    assert manager.sequence("history_toggle") == "Ctrl+Z"
    assert manager.last_error.startswith(
        "Не удалось прочитать назначения клавиш"
    )


def test_conflicting_saved_bindings_are_repaired_to_unique_defaults(
    tmp_path,
) -> None:
    path = tmp_path / "key_bindings.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "bindings": {
                    "delete_branch": "Ctrl+Z",
                    "history_toggle": "Ctrl+Z",
                    "undo_only": "Ctrl+Shift+Z",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manager = KeyBindingManager(storage_path=path)

    assert manager.sequence("delete_branch") == "Del"
    assert manager.sequence("history_toggle") == "Ctrl+Z"
    assert manager.sequence("undo_only") == "Ctrl+Shift+Z"
    assert "Конфликтующие" in manager.last_error

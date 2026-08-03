from __future__ import annotations

import json

from persona_training_lab.ui.keybindings.manager import KeyBindingManager


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


def test_key_binding_change_is_persisted_and_emitted(tmp_path) -> None:
    path = tmp_path / "key_bindings.json"
    manager = KeyBindingManager(storage_path=path)
    emissions: list[dict[str, str]] = []
    manager.bindings_changed.connect(lambda: emissions.append(manager.current_bindings()))

    result = manager.set_sequence("history_toggle", "Ctrl+Y")

    assert result.accepted is True
    assert result.changed is True
    assert manager.sequence("history_toggle") == "Ctrl+Y"
    assert len(emissions) == 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["bindings"]["history_toggle"] == "Ctrl+Y"

    restored = KeyBindingManager(storage_path=path)
    assert restored.sequence("history_toggle") == "Ctrl+Y"


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


def test_reset_binding_and_reset_all_restore_defaults(tmp_path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "key_bindings.json")
    assert manager.set_sequence("history_toggle", "Ctrl+Y").accepted
    assert manager.set_sequence("undo_only", "Ctrl+Shift+Y").accepted

    one = manager.reset_binding("history_toggle")
    assert one.accepted is True
    assert manager.sequence("history_toggle") == "Ctrl+Z"
    assert manager.sequence("undo_only") == "Ctrl+Shift+Y"

    all_result = manager.reset_all()
    assert all_result.accepted is True
    assert manager.sequence("history_toggle") == "Ctrl+Z"
    assert manager.sequence("undo_only") == "Ctrl+Shift+Z"


def test_corrupted_file_falls_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "key_bindings.json"
    path.write_text("{not-json", encoding="utf-8")

    manager = KeyBindingManager(storage_path=path)

    assert manager.sequence("history_toggle") == "Ctrl+Z"
    assert manager.last_error.startswith("Не удалось прочитать назначения клавиш")


def test_conflicting_saved_bindings_are_repaired_to_unique_defaults(tmp_path) -> None:
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
    assert "Конфликтующие назначения" in manager.last_error

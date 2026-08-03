from __future__ import annotations

from persona_training_lab.ui.agents.key_bindings import (
    AGENT_GRAPH_KEY_BINDINGS,
    AGENT_GRAPH_MOUSE_BINDINGS,
    agent_graph_key_bindings_by_id,
    agent_graph_mouse_bindings_by_id,
)


def test_agent_graph_key_bindings_have_unique_ids_and_sequences() -> None:
    ids = [binding.binding_id for binding in AGENT_GRAPH_KEY_BINDINGS]
    sequences = [binding.sequence for binding in AGENT_GRAPH_KEY_BINDINGS]

    assert len(ids) == len(set(ids))
    assert len(sequences) == len(set(sequences))
    assert set(agent_graph_key_bindings_by_id()) == set(ids)


def test_agent_graph_mouse_bindings_have_unique_ids() -> None:
    ids = [binding.binding_id for binding in AGENT_GRAPH_MOUSE_BINDINGS]

    assert len(ids) == len(set(ids))
    assert set(agent_graph_mouse_bindings_by_id()) == set(ids)
    assert {binding.target for binding in AGENT_GRAPH_MOUSE_BINDINGS} == {
        "node",
        "canvas",
    }
    assert {binding.trigger for binding in AGENT_GRAPH_MOUSE_BINDINGS} == {
        "click",
        "drag",
        "wheel",
    }


def test_agent_graph_key_bindings_describe_delete_toggle_and_undo_only_in_russian() -> None:
    bindings = agent_graph_key_bindings_by_id()

    assert bindings["delete_branch"].sequence == "Del"
    assert "Удалить" in bindings["delete_branch"].title

    assert bindings["history_toggle"].sequence == "Ctrl+Z"
    assert "Отменить или вернуть" in bindings["history_toggle"].title
    assert bindings["history_toggle"].auto_repeat is False

    assert bindings["undo_only"].sequence == "Ctrl+Shift+Z"
    assert "назад" in bindings["undo_only"].title
    assert bindings["undo_only"].auto_repeat is True


def test_agent_graph_mouse_defaults_preserve_current_canvas_controls() -> None:
    bindings = agent_graph_mouse_bindings_by_id()

    assert (bindings["open_node_menu"].button, bindings["open_node_menu"].modifier) == (
        "left",
        "none",
    )
    assert (bindings["pan_canvas_primary"].button, bindings["pan_canvas_primary"].modifier) == (
        "left",
        "none",
    )
    assert (bindings["pan_canvas_secondary"].button, bindings["pan_canvas_secondary"].modifier) == (
        "right",
        "none",
    )
    assert (bindings["move_node"].button, bindings["move_node"].modifier) == (
        "right",
        "none",
    )
    assert (bindings["move_subtree"].button, bindings["move_subtree"].modifier) == (
        "right",
        "shift",
    )
    assert (bindings["zoom_canvas"].button, bindings["zoom_canvas"].modifier) == (
        "wheel",
        "none",
    )

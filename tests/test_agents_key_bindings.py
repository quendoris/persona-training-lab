from __future__ import annotations

from persona_training_lab.ui.agents.key_bindings import AGENT_GRAPH_KEY_BINDINGS, agent_graph_key_bindings_by_id


def test_agent_graph_key_bindings_have_unique_ids_and_sequences() -> None:
    ids = [binding.binding_id for binding in AGENT_GRAPH_KEY_BINDINGS]
    sequences = [binding.sequence for binding in AGENT_GRAPH_KEY_BINDINGS]

    assert len(ids) == len(set(ids))
    assert len(sequences) == len(set(sequences))
    assert set(agent_graph_key_bindings_by_id()) == set(ids)


def test_agent_graph_key_bindings_describe_delete_and_undo_actions_in_russian() -> None:
    bindings = agent_graph_key_bindings_by_id()

    assert bindings["delete_branch"].sequence == "Del"
    assert "Удалить" in bindings["delete_branch"].title
    assert bindings["undo_once"].sequence == "Ctrl+Z"
    assert "Отменить" in bindings["undo_once"].title
    assert bindings["undo_many"].sequence == "Ctrl+Shift+Z"
    assert bindings["undo_many"].auto_repeat is True

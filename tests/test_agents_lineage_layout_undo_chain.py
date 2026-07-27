from __future__ import annotations

from persona_training_lab.ui.agents.lineage_state import LineageStateStore


def _layout(x: float) -> dict[str, object]:
    offsets = {} if x == 0 else {"snapshot": {"x": x, "y": 0.0}}
    return {"schema": 1, "offsets": offsets}


def test_repeated_strict_undo_walks_back_through_layout_moves(tmp_path) -> None:
    store = LineageStateStore(tmp_path / "state.json")
    layouts = tuple(_layout(x) for x in (0.0, 10.0, 20.0, 30.0))

    store.record_layout_action("move 1", layouts[0])
    store.record_layout_action("move 2", layouts[1])
    store.record_layout_action("move 3", layouts[2])

    current = layouts[3]
    restored = []
    directions = []
    for _ in range(3):
        transition = store.undo_only(current)
        assert transition is not None
        directions.append(transition.direction)
        restored.append(transition.layout_snapshot)
        current = transition.layout_snapshot

    assert directions == ["undo", "undo", "undo"]
    assert restored == [layouts[2], layouts[1], layouts[0]]
    assert store.can_undo() is False
    assert store.can_redo() is True

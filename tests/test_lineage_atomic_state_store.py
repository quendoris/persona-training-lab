from __future__ import annotations

import json

import pytest

from persona_training_lab.ui.agents import lineage_state_atomic
from persona_training_lab.ui.agents.lineage import LineageVersionNode
from persona_training_lab.ui.agents.lineage_state_atomic import (
    AtomicLineageStateStore,
)


def _base_nodes() -> tuple[LineageVersionNode, ...]:
    return (
        LineageVersionNode(
            "base",
            None,
            "Base",
            "root",
            "source",
            "good",
            "main",
            level=0,
        ),
        LineageVersionNode(
            "snapshot",
            "base",
            "Version",
            "snapshot",
            "ready",
            "good",
            "current",
            is_current=True,
            level=1,
        ),
    )


def _node_ids(store: AtomicLineageStateStore) -> set[str]:
    return {node.node_id for node in store.apply(_base_nodes())}


def test_atomic_store_persists_complete_state_and_reloads_it(tmp_path) -> None:
    path = tmp_path / "lineage.json"
    store = AtomicLineageStateStore(path)

    branch_id = store.continue_from("snapshot")
    store.rename_node(branch_id, "durable branch")

    reloaded = AtomicLineageStateStore(path)
    nodes = {node.node_id: node for node in reloaded.apply(_base_nodes())}
    assert nodes[branch_id].title == "durable branch"
    assert json.loads(path.read_text(encoding="utf-8"))["schema"] == 5


def test_atomic_store_restores_memory_and_file_when_replace_fails(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "lineage.json"
    store = AtomicLineageStateStore(path)
    stable_id = store.continue_from("snapshot")
    before = path.read_text(encoding="utf-8")

    def fail_replace(_source, _target) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(lineage_state_atomic.os, "replace", fail_replace)

    with pytest.raises(OSError, match="disk full"):
        store.continue_from(stable_id)

    assert _node_ids(store) == {"base", "snapshot", stable_id}
    assert path.read_text(encoding="utf-8") == before
    assert tuple(tmp_path.glob(f".{path.name}.*.tmp")) == ()


def test_transaction_snapshot_restores_lineage_without_history_pollution(
    tmp_path,
) -> None:
    path = tmp_path / "lineage.json"
    store = AtomicLineageStateStore(path)
    root_id = store.continue_from("snapshot")
    transaction_snapshot = store.capture_transaction_state()

    child_id = store.continue_from(root_id)
    assert child_id in _node_ids(store)
    store.restore_transaction_state(transaction_snapshot)

    assert _node_ids(store) == {"base", "snapshot", root_id}
    assert _node_ids(AtomicLineageStateStore(path)) == {
        "base",
        "snapshot",
        root_id,
    }
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == transaction_snapshot

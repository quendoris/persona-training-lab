from __future__ import annotations

import json

from persona_training_lab.ui.agents.lineage import LineageVersionNode
from persona_training_lab.ui.agents.lineage_state import LineageStateStore


def _base_nodes() -> tuple[LineageVersionNode, ...]:
    return (
        LineageVersionNode(
            "snapshot",
            None,
            "Version",
            "snapshot",
            "ready",
            "good",
            "current",
            is_current=True,
            level=0,
        ),
    )


def test_schema_six_user_title_that_looks_generated_survives_restart(
    tmp_path,
) -> None:
    path = tmp_path / "state.json"
    store = LineageStateStore(path)
    branch_id = store.continue_from("snapshot")
    deliberate_title = "Version · branch 001"

    assert store.rename_node(branch_id, deliberate_title) is True

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == 6
    assert payload["custom_nodes"][0]["title"] == deliberate_title

    reloaded = LineageStateStore(path)
    nodes = {node.node_id: node for node in reloaded.apply(_base_nodes())}

    assert nodes[branch_id].title == deliberate_title
    payload_after_reload = json.loads(path.read_text(encoding="utf-8"))
    assert payload_after_reload["custom_nodes"][0]["title"] == deliberate_title

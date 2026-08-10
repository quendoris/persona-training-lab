from __future__ import annotations

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.agents.lineage import build_version_lineage
from persona_training_lab.ui.viewmodels.agents import VersionNodeView


def test_pending_delta_becomes_side_branch_from_snapshot() -> None:
    nodes = (
        VersionNodeView("base", 0, "Base · qwen", "root", "source", "good", "main"),
        VersionNodeView("dataset", 1, "Dataset · v1", "dataset", "ok", "good", "main"),
        VersionNodeView("training", 2, "Train · run", "train", "ok", "good", "main"),
        VersionNodeView("snapshot", 3, "Version · model", "snapshot", "ok", "good", "current"),
        VersionNodeView("portrait", 4, "Portrait · p1", "portrait", "ok", "good", "main"),
        VersionNodeView("delta", 5, "Delta · latest - previous", "needs second portrait", "wait", "pending", "main"),
    )

    lineage = {node.node_id: node for node in build_version_lineage(nodes)}

    assert lineage["snapshot"].is_current is True
    assert lineage["portrait"].parent_id == "snapshot"
    assert lineage["delta"].parent_id == "snapshot"
    assert lineage["delta"].branch_note == "side"
    assert lineage["delta"].tone == "pending"
    title = lineage["delta"].title
    assert isinstance(title, UserMessage)
    assert title.key == "agents.node.pending_delta.title"


def test_ready_delta_stays_on_mainline_after_portrait() -> None:
    nodes = (
        VersionNodeView("base", 0, "Base · qwen", "root", "source", "good", "main"),
        VersionNodeView("snapshot", 1, "Version · model", "snapshot", "ok", "good", "current"),
        VersionNodeView("portrait", 2, "Portrait · p1", "portrait", "ok", "good", "main"),
        VersionNodeView("delta", 3, "Delta · latest - previous", "+0.1", "ready", "good", "main"),
    )

    lineage = {node.node_id: node for node in build_version_lineage(nodes)}

    assert lineage["delta"].parent_id == "portrait"
    assert lineage["delta"].branch_note == "main"
    assert lineage["delta"].tone == "good"


def test_pending_middle_node_branches_while_mainline_continues() -> None:
    nodes = (
        VersionNodeView("base", 0, "Base · qwen", "root", "source", "good", "main"),
        VersionNodeView("dataset", 1, "Dataset · pending", "dataset", "wait", "pending", "main"),
        VersionNodeView("training", 2, "Train · run", "train", "ok", "good", "main"),
        VersionNodeView("snapshot", 3, "Version · model", "snapshot", "ok", "good", "current"),
    )

    lineage = {node.node_id: node for node in build_version_lineage(nodes)}

    assert lineage["dataset"].parent_id == "base"
    assert lineage["dataset"].branch_note == "side"
    assert lineage["dataset"].tone == "pending"
    assert lineage["training"].parent_id == "base"
    assert lineage["training"].branch_note == "main"
    assert lineage["snapshot"].parent_id == "training"

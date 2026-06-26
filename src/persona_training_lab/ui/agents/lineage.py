from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from persona_training_lab.ui.viewmodels.agents import VersionNodeView


@dataclass(slots=True, frozen=True)
class LineageVersionNode:
    node_id: str
    parent_id: str | None
    title: str
    subtitle: str
    status: str
    tone: str
    branch_note: str
    is_current: bool = False
    level: int = 0


PARENT_BY_NODE_ID = {
    "base": None,
    "dataset": "base",
    "training": "dataset",
    "snapshot": "training",
    "portrait": "snapshot",
    "delta": "portrait",
    "accepted_delta": "portrait",
    "unclear_branch": "snapshot",
}


ROOT_NODE_IDS = {"base"}
MAINLINE_NOTES = {"main", "current"}


def build_version_lineage(raw_nodes: Iterable[VersionNodeView]) -> tuple[LineageVersionNode, ...]:
    nodes = list(raw_nodes)
    by_id = {node.node_id: node for node in nodes}
    parent_by_id = {node.node_id: _parent_id(node) for node in nodes}
    level_by_id = _visual_level_by_id(nodes, parent_by_id)
    side_ids = _side_branch_node_ids(nodes, by_id, parent_by_id)
    result: list[LineageVersionNode] = []
    for node in nodes:
        node_id = node.node_id
        parent_id = _effective_parent_id(node, parent_by_id, side_ids)
        branch_note = "side" if node_id in side_ids else node.branch_note
        tone = node.tone
        title = node.title
        subtitle = node.subtitle
        status = node.status
        is_current = node.branch_note == "current"
        level = level_by_id.get(node_id, 0)
        if _is_pending_delta(node):
            parent_id = "snapshot" if "snapshot" in by_id else parent_id
            branch_note = "side"
            title = "Version · pending branch"
            subtitle = "Боковая ветка: спорный результат, пока не продолжает зелёную mainline."
            status = "не определена"
            tone = "pending"
            if "snapshot" in level_by_id:
                level = level_by_id["snapshot"] + 1
        result.append(
            LineageVersionNode(
                node_id=node_id,
                parent_id=parent_id,
                title=title,
                subtitle=subtitle,
                status=status,
                tone=tone,
                branch_note=branch_note,
                is_current=is_current,
                level=level,
            )
        )
    return tuple(result)


def _visual_level_by_id(
    nodes: list[VersionNodeView],
    parent_by_id: dict[str, str | None],
) -> dict[str, int]:
    explicit = {node.node_id: getattr(node, "depth") for node in nodes if hasattr(node, "depth")}
    if explicit:
        return {node.node_id: int(explicit.get(node.node_id, index)) for index, node in enumerate(nodes)}
    by_id = {node.node_id: node for node in nodes}
    cache: dict[str, int] = {}

    def level(node_id: str) -> int:
        if node_id in cache:
            return cache[node_id]
        parent_id = parent_by_id.get(node_id)
        cache[node_id] = 0 if parent_id is None or parent_id not in by_id else level(parent_id) + 1
        return cache[node_id]

    for node in nodes:
        level(node.node_id)
    return cache


def _side_branch_node_ids(
    nodes: list[VersionNodeView],
    by_id: dict[str, VersionNodeView],
    parent_by_id: dict[str, str | None],
) -> set[str]:
    side_ids: set[str] = set()
    for node in nodes:
        if not _should_branch_pending_node(node):
            continue
        parent_id = parent_by_id.get(node.node_id)
        if parent_id is None or parent_id not in by_id:
            continue
        if _has_mainline_child_after(node.node_id, nodes, parent_by_id):
            side_ids.add(node.node_id)
    return side_ids


def _should_branch_pending_node(node: VersionNodeView) -> bool:
    return (
        node.node_id not in ROOT_NODE_IDS
        and node.branch_note in MAINLINE_NOTES
        and node.branch_note != "current"
        and node.tone == "pending"
    )


def _has_mainline_child_after(
    node_id: str,
    nodes: list[VersionNodeView],
    parent_by_id: dict[str, str | None],
) -> bool:
    for child in nodes:
        if parent_by_id.get(child.node_id) != node_id:
            continue
        if child.branch_note in MAINLINE_NOTES:
            return True
    return False


def _effective_parent_id(
    node: VersionNodeView,
    parent_by_id: dict[str, str | None],
    side_ids: set[str],
) -> str | None:
    parent_id = parent_by_id.get(node.node_id)
    while parent_id in side_ids:
        parent_id = parent_by_id.get(parent_id)
    return parent_id


def _parent_id(node: VersionNodeView) -> str | None:
    explicit = getattr(node, "parent_id", None)
    if explicit is not None:
        return explicit
    return PARENT_BY_NODE_ID.get(node.node_id)


def _is_pending_delta(node: VersionNodeView) -> bool:
    return node.node_id == "delta" and node.tone == "pending"

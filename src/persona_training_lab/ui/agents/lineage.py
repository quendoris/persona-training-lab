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


def build_version_lineage(raw_nodes: Iterable[VersionNodeView]) -> tuple[LineageVersionNode, ...]:
    nodes = list(raw_nodes)
    by_id = {node.node_id: node for node in nodes}
    result: list[LineageVersionNode] = []
    for node in nodes:
        node_id = node.node_id
        parent_id = _parent_id(node)
        branch_note = _branch_note(node)
        tone = node.tone
        title = node.title
        subtitle = node.subtitle
        status = node.status
        is_current = node.branch_note == "current"
        if _is_pending_delta(node):
            parent_id = "snapshot" if "snapshot" in by_id else parent_id
            branch_note = "side"
            title = "Version · pending branch"
            subtitle = "Боковая ветка: спорный результат, пока не продолжает зелёную mainline."
            status = "не определена"
            tone = "pending"
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
            )
        )
    return tuple(result)


def _parent_id(node: VersionNodeView) -> str | None:
    explicit = getattr(node, "parent_id", None)
    if explicit is not None:
        return explicit
    return PARENT_BY_NODE_ID.get(node.node_id)


def _branch_note(node: VersionNodeView) -> str:
    if _is_pending_delta(node):
        return "side"
    return node.branch_note


def _is_pending_delta(node: VersionNodeView) -> bool:
    return node.node_id == "delta" and node.tone == "pending"

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LayoutInputNode:
    node_id: str
    parent_id: str | None
    title: str
    is_side: bool
    source_level: int = 0


@dataclass(frozen=True, slots=True)
class BranchGroup:
    root_id: str
    parent_id: str | None
    ids: tuple[str, ...]
    start: int
    end: int
    width: float


@dataclass(frozen=True, slots=True)
class VersionGraphLayout:
    levels: dict[str, int]
    lanes: dict[str, int]
    lane_offsets: dict[int, float]


RIGHT_LANE_MINIMUM = 112.0
LEFT_LANE_MINIMUM = 112.0
LANE_GAP = 76.0
MAIN_LABEL_GAP = 78.0
LEFT_LABEL_GAP = 76.0
INTERVAL_PADDING = 1
ADJACENT_LABEL_LIMIT = 190.0


def build_version_graph_layout(nodes: tuple[LayoutInputNode, ...], label_widths: dict[str, float]) -> VersionGraphLayout:
    by_id = {node.node_id: node for node in nodes}
    children = _children_by_id(nodes)
    levels = _display_levels(nodes, by_id, children)
    groups = _branch_groups(nodes, by_id, children, levels, label_widths)
    lanes = _lanes(nodes, by_id, groups)
    offsets = _lane_offsets(nodes, by_id, lanes, label_widths)
    return VersionGraphLayout(levels=levels, lanes=lanes, lane_offsets=offsets)


def _children_by_id(nodes: tuple[LayoutInputNode, ...]) -> dict[str | None, list[str]]:
    children: dict[str | None, list[str]] = {}
    for node in nodes:
        children.setdefault(node.parent_id, []).append(node.node_id)
    return children


def _display_levels(
    nodes: tuple[LayoutInputNode, ...],
    by_id: dict[str, LayoutInputNode],
    children: dict[str | None, list[str]],
) -> dict[str, int]:
    levels: dict[str, int] = {}

    def assign(node_id: str, level: int) -> None:
        if node_id in levels or node_id not in by_id:
            return
        levels[node_id] = level
        node_children = [child_id for child_id in children.get(node_id, []) if child_id in by_id]
        side_children = [child_id for child_id in node_children if by_id[child_id].is_side]
        main_children = [child_id for child_id in node_children if not by_id[child_id].is_side]
        for offset, child_id in enumerate(side_children):
            assign(child_id, level + 1 + offset)
        main_level = level + 1 + len(side_children)
        for offset, child_id in enumerate(main_children):
            assign(child_id, main_level + offset)

    for root_id in children.get(None, []):
        assign(root_id, 0)
    for node in nodes:
        if node.node_id not in levels:
            parent_level = (
                levels.get(node.parent_id, node.source_level - 1)
                if node.parent_id is not None
                else node.source_level - 1
            )
            assign(node.node_id, max(0, parent_level + 1))
    return levels


def _branch_groups(
    nodes: tuple[LayoutInputNode, ...],
    by_id: dict[str, LayoutInputNode],
    children: dict[str | None, list[str]],
    levels: dict[str, int],
    label_widths: dict[str, float],
) -> list[BranchGroup]:
    groups: list[BranchGroup] = []
    for node in nodes:
        if not node.is_side or not _is_branch_root(node, by_id, children):
            continue
        ids = _collect_branch_ids(node.node_id, by_id, children)
        used_levels = [levels[node_id] for node_id in ids if node_id in levels]
        if not used_levels:
            continue
        width = max((label_widths.get(node_id, 120.0) for node_id in ids), default=120.0)
        groups.append(
            BranchGroup(
                root_id=node.node_id,
                parent_id=node.parent_id,
                ids=ids,
                start=min(used_levels),
                end=max(used_levels),
                width=width,
            )
        )
    return groups


def _is_branch_root(node: LayoutInputNode, by_id: dict[str, LayoutInputNode], children: dict[str | None, list[str]]) -> bool:
    parent = by_id.get(node.parent_id or "")
    if parent is None or not parent.is_side:
        return True
    side_siblings = [child_id for child_id in children.get(parent.node_id, []) if by_id.get(child_id) and by_id[child_id].is_side]
    return bool(side_siblings and side_siblings[0] != node.node_id)


def _collect_branch_ids(root_id: str, by_id: dict[str, LayoutInputNode], children: dict[str | None, list[str]]) -> tuple[str, ...]:
    result: list[str] = []
    current_id: str | None = root_id
    while current_id is not None and current_id in by_id:
        result.append(current_id)
        side_children = [child_id for child_id in children.get(current_id, []) if child_id in by_id and by_id[child_id].is_side]
        current_id = side_children[0] if side_children else None
    return tuple(result)


def _lanes(nodes: tuple[LayoutInputNode, ...], by_id: dict[str, LayoutInputNode], groups: list[BranchGroup]) -> dict[str, int]:
    lanes = {node.node_id: 0 for node in nodes}
    occupancy: dict[int, list[BranchGroup]] = {}
    pending = sorted(groups, key=lambda item: (item.end, item.start), reverse=True)
    while pending:
        remaining: list[BranchGroup] = []
        progressed = False
        for group in pending:
            parent = by_id.get(group.parent_id or "")
            parent_lane = lanes.get(group.parent_id or "", 0)
            if parent is not None and parent.is_side and parent_lane == 0:
                remaining.append(group)
                continue
            preferred_sign = _sign(parent_lane) if parent is not None and parent.is_side else 0
            lane = _choose_lane(group, occupancy, preferred_sign)
            for node_id in group.ids:
                lanes[node_id] = lane
            occupancy.setdefault(lane, []).append(group)
            progressed = True
        if not progressed:
            # Defensive fallback for malformed/cyclic input: keep drawing instead of
            # producing a crossing through the mainline by accident.
            group = remaining.pop(0)
            lane = _choose_lane(group, occupancy, 1)
            for node_id in group.ids:
                lanes[node_id] = lane
            occupancy.setdefault(lane, []).append(group)
        pending = remaining
    return lanes


def _choose_lane(group: BranchGroup, occupancy: dict[int, list[BranchGroup]], preferred_sign: int) -> int:
    for lane in _candidate_lanes(preferred_sign):
        if _lane_is_free(lane, group, occupancy):
            return lane
    step = max((abs(lane) for lane in occupancy), default=0) + 1
    return step if preferred_sign >= 0 else -step


def _candidate_lanes(preferred_sign: int = 0) -> tuple[int, ...]:
    lanes: list[int] = []
    if preferred_sign > 0:
        return tuple(range(1, 24))
    if preferred_sign < 0:
        return tuple(-step for step in range(1, 24))
    for step in range(1, 24):
        lanes.extend((step, -step))
    return tuple(lanes)


def _lane_is_free(lane: int, group: BranchGroup, occupancy: dict[int, list[BranchGroup]]) -> bool:
    for other in occupancy.get(lane, []):
        if group.start <= other.end + INTERVAL_PADDING and other.start <= group.end + INTERVAL_PADDING:
            return False
        if abs(group.start - other.end) <= 1 or abs(other.start - group.end) <= 1:
            if group.width + other.width > ADJACENT_LABEL_LIMIT:
                return False
    return True


def _lane_offsets(
    nodes: tuple[LayoutInputNode, ...],
    by_id: dict[str, LayoutInputNode],
    lanes: dict[str, int],
    label_widths: dict[str, float],
) -> dict[int, float]:
    lane_ids = sorted(set(lanes.values()))
    lane_widths: dict[int, float] = {}
    lane_minimums: dict[int, float] = {}
    for node in nodes:
        lane = lanes.get(node.node_id, 0)
        if lane == 0:
            continue
        lane_widths[lane] = max(lane_widths.get(lane, 0.0), label_widths.get(node.node_id, 120.0))
        parent = by_id.get(node.parent_id or "")
        if parent is not None:
            lane_minimums[lane] = max(lane_minimums.get(lane, 0.0), label_widths.get(parent.node_id, 120.0) + MAIN_LABEL_GAP)

    offsets: dict[int, float] = {0: 0.0}
    previous_offset = 0.0
    previous_width = 0.0
    for lane in [item for item in lane_ids if item > 0]:
        minimum = max(lane_minimums.get(lane, 0.0), RIGHT_LANE_MINIMUM)
        previous_offset = max(previous_offset + previous_width + LANE_GAP, minimum)
        offsets[lane] = previous_offset
        previous_width = lane_widths.get(lane, 120.0)

    previous_distance = 0.0
    for lane in sorted((item for item in lane_ids if item < 0), reverse=True):
        width = lane_widths.get(lane, 120.0)
        minimum = max(width + LEFT_LABEL_GAP, LEFT_LANE_MINIMUM)
        previous_distance = max(previous_distance + width + LANE_GAP, minimum)
        offsets[lane] = -previous_distance
    return offsets


def _sign(value: int) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0

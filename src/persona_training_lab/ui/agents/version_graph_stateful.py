from __future__ import annotations

from persona_training_lab.ui.agents.version_graph_locked import VersionGraphCanvas as LockableVersionGraphCanvas
from persona_training_lab.ui.viewmodels.agents import VersionNodeView


class VersionGraphCanvas(LockableVersionGraphCanvas):
    def set_nodes(self, nodes: tuple[VersionNodeView, ...]) -> None:
        self._nodes = nodes
        ids = {node.node_id for node in nodes}
        if self._selected_node_id not in ids:
            self._selected_node_id = self.current_node_id()
        self._hit_rects.clear()
        self._refresh_size()
        self.updateGeometry()
        self.update()

    def _lanes(self) -> dict[str, int]:
        children = self._children_by_id()
        by_id = {node.node_id: node for node in self._nodes}
        levels = self._display_levels()
        lanes = {node.node_id: 0 for node in self._nodes}
        occupancy: dict[int, list[tuple[int, int, float]]] = {}
        groups = self._branch_groups(children, by_id, levels)

        # Снизу вверх: новые/нижние ветки первыми занимают ближайшие lanes.
        # Старые длинные ветки, которые доходят до них, уходят наружу.
        for group in sorted(groups, key=lambda item: (item["end"], item["start"]), reverse=True):
            lane = self._choose_free_lane(group, occupancy)
            for node_id in group["ids"]:
                lanes[str(node_id)] = lane
            occupancy.setdefault(lane, []).append((int(group["start"]), int(group["end"]), float(group["width"])))
        return lanes

    def _branch_groups(
        self,
        children: dict[str, list[str]],
        by_id: dict[str, object],
        levels: dict[str, int],
    ) -> list[dict[str, object]]:
        groups: list[dict[str, object]] = []
        for node in self._nodes:
            if not self._side(node):
                continue
            parent_id = self._parent(node)
            parent = by_id.get(parent_id) if parent_id is not None else None
            if parent is not None and self._side(parent):
                continue
            ids = self._collect_branch_ids(node.node_id, children, by_id)
            used_levels = [levels.get(node_id, self._level(by_id[node_id])) for node_id in ids if node_id in by_id]
            if not used_levels:
                continue
            groups.append(
                {
                    "ids": tuple(ids),
                    "start": min(used_levels),
                    "end": max(used_levels),
                    "width": max((self._label_width(by_id[node_id].title) for node_id in ids if node_id in by_id), default=120.0),
                }
            )
        return groups

    def _collect_branch_ids(self, root_id: str, children: dict[str, list[str]], by_id: dict[str, object]) -> tuple[str, ...]:
        result: list[str] = []

        def collect(node_id: str) -> None:
            if node_id in result or node_id not in by_id:
                return
            result.append(node_id)
            for child_id in children.get(node_id, []):
                collect(child_id)

        collect(root_id)
        return tuple(result)

    def _choose_free_lane(self, group: dict[str, object], occupancy: dict[int, list[tuple[int, int, float]]]) -> int:
        for lane in self._candidate_lanes():
            if self._lane_is_free(lane, group, occupancy):
                return lane
        return max((abs(lane) for lane in occupancy), default=0) + 1

    def _candidate_lanes(self) -> tuple[int, ...]:
        result: list[int] = []
        for step in range(1, 20):
            result.extend((step, -step))
        return tuple(result)

    def _lane_is_free(self, lane: int, group: dict[str, object], occupancy: dict[int, list[tuple[int, int, float]]]) -> bool:
        start = int(group["start"])
        end = int(group["end"])
        width = float(group["width"])
        for other_start, other_end, other_width in occupancy.get(lane, []):
            if start <= other_end + 1 and other_start <= end + 1:
                return False
            if abs(start - other_end) <= 1 or abs(other_start - end) <= 1:
                if width + other_width > 180:
                    return False
        return True

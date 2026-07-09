from __future__ import annotations

from persona_training_lab.ui.agents.version_graph_layout_engine import LayoutInputNode, build_version_graph_layout
from persona_training_lab.ui.agents.version_graph_stateful import VersionGraphCanvas as StatefulVersionGraphCanvas


class VersionGraphCanvas(StatefulVersionGraphCanvas):
    def _layout_inputs(self) -> tuple[LayoutInputNode, ...]:
        return tuple(
            LayoutInputNode(
                node_id=node.node_id,
                parent_id=self._parent(node),
                title=self._display_label(node.title),
                is_side=self._side(node),
                source_level=self._level(node),
            )
            for node in self._nodes
        )

    def _tree_layout(self):
        inputs = self._layout_inputs()
        label_widths = {node.node_id: self._label_width(node.title) for node in self._nodes}
        return build_version_graph_layout(inputs, label_widths)

    def _display_levels(self) -> dict[str, int]:
        return self._tree_layout().levels

    def _lanes(self) -> dict[str, int]:
        return self._tree_layout().lanes

    def _lane_offsets(self, lanes: dict[str, int]) -> dict[int, float]:
        # lanes is accepted for compatibility with the parent canvas API; the
        # pure engine returns offsets from the same layout pass that produced lanes.
        return self._tree_layout().lane_offsets

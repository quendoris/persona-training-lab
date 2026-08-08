from __future__ import annotations

from typing import Any

from persona_training_lab.ui.agents.version_graph_interactions import (
    VersionGraphCanvas as InteractionVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_layout_engine import (
    LayoutInputNode,
    build_version_graph_layout,
)


class VersionGraphCanvas(InteractionVersionGraphCanvas):
    """Own the authoritative computed tree layout and its cache."""

    def __init__(self, nodes) -> None:
        self._layout_cache_key: tuple[object, ...] | None = None
        self._layout_cache: Any | None = None
        super().__init__(nodes)

    def set_nodes(self, nodes) -> None:
        self._invalidate_tree_layout()
        super().set_nodes(nodes)

    def _invalidate_tree_layout(self) -> None:
        self._layout_cache_key = None
        self._layout_cache = None

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
        label_widths = {
            node.node_id: self._label_width(node.title) for node in self._nodes
        }
        key = (
            tuple(
                (
                    node.node_id,
                    node.parent_id,
                    node.title,
                    node.is_side,
                    node.source_level,
                )
                for node in inputs
            ),
            tuple(sorted(label_widths.items())),
        )
        if self._layout_cache_key != key or self._layout_cache is None:
            self._layout_cache_key = key
            self._layout_cache = build_version_graph_layout(inputs, label_widths)
        return self._layout_cache

    def _display_levels(self) -> dict[str, int]:
        return self._tree_layout().levels

    def _lanes(self) -> dict[str, int]:
        return self._tree_layout().lanes

    def _lane_offsets(self, lanes: dict[str, int]) -> dict[int, float]:
        return self._tree_layout().lane_offsets

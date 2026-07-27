from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from persona_training_lab.ui.agents.version_graph_layout_engine import LayoutInputNode, build_version_graph_layout
from persona_training_lab.ui.agents.version_graph_stateful import VersionGraphCanvas as StatefulVersionGraphCanvas


class VersionGraphCanvas(StatefulVersionGraphCanvas):
    def __init__(self, nodes) -> None:
        # The base canvas calculates its size during __init__, which already calls
        # _display_levels(). Cache fields must therefore exist before super().__init__.
        self._layout_cache_key: tuple[object, ...] | None = None
        self._layout_cache: Any | None = None
        super().__init__(nodes)

    def set_nodes(self, nodes) -> None:
        self._invalidate_tree_layout()
        super().set_nodes(nodes)

    def reset_zoom(self) -> None:
        super().reset_zoom()

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        old_zoom = self._zoom
        new_zoom = max(0.65, min(1.8, old_zoom + (0.08 if delta > 0 else -0.08)))
        if new_zoom == old_zoom:
            event.accept()
            return

        # Emit before resizing the canvas. The screen captures the old scrollbar
        # values synchronously, then applies the corrected values after resize.
        anchor = event.position()
        self.zoom_anchor_requested.emit(anchor, old_zoom, new_zoom)
        self._set_zoom(new_zoom)
        event.accept()

    def forget_layout_nodes(self, node_ids: Iterable[str]) -> None:
        removed = set(node_ids)
        for node_id in removed:
            self._node_offsets.pop(node_id, None)
        if getattr(self, "_menu_node_id", None) in removed:
            self._menu_node_id = None
        if removed:
            self._save_offsets()
            self.update()

    def close_node_menu(self) -> None:
        self._menu_node_id = None
        self.update()

    def _menu_actions(self) -> tuple[tuple[str, str], ...]:
        actions: list[tuple[str, str]] = [
            ("make_current", "Сделать актуальной"),
            ("mark_good", "Пометить удачной"),
            ("mark_pending", "Пометить спорной"),
            ("mark_bad", "Пометить неудачной"),
            ("continue", "Продолжить от этой точки"),
        ]
        node = next((item for item in self._nodes if item.node_id == self._menu_node_id), None)
        if node is not None and node.node_id.startswith("branch_"):
            actions.extend(
                (
                    ("rename", "Переименовать ветку"),
                    (
                        "archive_toggle",
                        "Вернуть из архива" if getattr(node, "status", "") == "архивная" else "Архивировать ветку",
                    ),
                    ("delete_subtree", "Удалить ветку и поддерево"),
                )
            )
        actions.extend(
            (
                ("center", "Центрировать на точке"),
                ("reset_node", "Сбросить смещение точки"),
                ("reset_subtree", "Сбросить смещение поддерева"),
            )
        )
        return tuple(actions)

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
        label_widths = {node.node_id: self._label_width(node.title) for node in self._nodes}
        key = (
            tuple((node.node_id, node.parent_id, node.title, node.is_side, node.source_level) for node in inputs),
            tuple(sorted(label_widths.items())),
        )
        if getattr(self, "_layout_cache_key", None) != key or getattr(self, "_layout_cache", None) is None:
            self._layout_cache_key = key
            self._layout_cache = build_version_graph_layout(inputs, label_widths)
        return self._layout_cache

    def _display_levels(self) -> dict[str, int]:
        return self._tree_layout().levels

    def _lanes(self) -> dict[str, int]:
        return self._tree_layout().lanes

    def _lane_offsets(self, lanes: dict[str, int]) -> dict[int, float]:
        # lanes is accepted for compatibility with the parent canvas API; the
        # pure engine returns offsets from the same layout pass that produced lanes.
        return self._tree_layout().lane_offsets

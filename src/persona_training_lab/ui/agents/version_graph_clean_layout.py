from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QMouseEvent

from persona_training_lab.ui.agents.drag_scope import drag_history_label, drag_target_ids
from persona_training_lab.ui.agents.version_graph_interactions import VersionGraphCanvas as InteractionVersionGraphCanvas
from persona_training_lab.ui.agents.version_graph_layout_engine import LayoutInputNode, build_version_graph_layout


class VersionGraphCanvas(InteractionVersionGraphCanvas):
    layout_action_committed = Signal(str, object, bool)

    def __init__(self, nodes) -> None:
        self._layout_cache_key: tuple[object, ...] | None = None
        self._layout_cache: Any | None = None
        self._history_action_text: str | None = None
        self._drag_history_before: dict[str, Any] | None = None
        self._drag_history_moved_node = False
        self._drag_history_moved_subtree = False
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
        anchor = event.position()
        self.zoom_anchor_requested.emit(anchor, old_zoom, new_zoom)
        self._set_zoom(new_zoom)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_history_before = None
        self._drag_history_moved_node = False
        self._drag_history_moved_subtree = False
        if event.button() == Qt.MouseButton.RightButton and not self.layout_locked():
            node_id = self._node_at(event.position())
            if node_id is not None:
                self._drag_history_before = self.layout_snapshot()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        node_id = getattr(self, "_drag_node_id", None)
        drag_mode = getattr(self, "_drag_mode", None)
        is_node_drag = (
            node_id is not None
            and drag_mode in {"node", "subtree"}
            and bool(event.buttons() & Qt.MouseButton.RightButton)
        )
        scope_is_subtree = False
        before_move: dict[str, Any] | None = None
        if is_node_drag:
            scope_is_subtree = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            subtree_ids = self._subtree_node_ids(node_id)
            self._drag_mode = "subtree" if scope_is_subtree else "node"
            self._drag_target_ids = drag_target_ids(
                node_id,
                subtree_ids,
                shift_down=scope_is_subtree,
            )
            before_move = self.layout_snapshot()

        super().mouseMoveEvent(event)

        if before_move is not None and before_move != self.layout_snapshot():
            if scope_is_subtree:
                self._drag_history_moved_subtree = True
            else:
                self._drag_history_moved_node = True

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        before = self._drag_history_before
        moved_node = self._drag_history_moved_node
        moved_subtree = self._drag_history_moved_subtree
        super().mouseReleaseEvent(event)
        self._drag_history_before = None
        self._drag_history_moved_node = False
        self._drag_history_moved_subtree = False
        if before is not None and before != self.layout_snapshot():
            label = drag_history_label(moved_node=moved_node, moved_subtree=moved_subtree)
            self.layout_action_committed.emit(label, before, False)

    def layout_snapshot(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "offsets": {
                node_id: {"x": point.x(), "y": point.y()}
                for node_id, point in sorted(self._node_offsets.items())
                if point.x() or point.y()
            },
        }

    def restore_layout_snapshot(self, snapshot: dict[str, Any]) -> None:
        if not isinstance(snapshot, dict) or "offsets" not in snapshot:
            return
        raw_offsets = snapshot.get("offsets", {})
        if not isinstance(raw_offsets, dict):
            return
        known_ids = {node.node_id for node in self._nodes}
        restored: dict[str, QPointF] = {}
        for node_id, raw in raw_offsets.items():
            if node_id not in known_ids or not isinstance(raw, dict):
                continue
            try:
                point = QPointF(float(raw.get("x", 0.0)), float(raw.get("y", 0.0)))
            except (TypeError, ValueError):
                continue
            if point.x() or point.y():
                restored[node_id] = point
        self._node_offsets = restored
        self._layout_dirty = False
        self._save_offsets()
        self.update()

    def reset_layout(self) -> None:
        before = self.layout_snapshot()
        super().reset_layout()
        if before != self.layout_snapshot():
            self.layout_action_committed.emit("полный сброс раскладки", before, True)

    def reset_node_layout(self, node_id: str) -> None:
        before = self.layout_snapshot()
        super().reset_node_layout(node_id)
        if before != self.layout_snapshot():
            self.layout_action_committed.emit("сброс смещения точки", before, False)

    def reset_subtree_layout(self, node_id: str) -> None:
        before = self.layout_snapshot()
        super().reset_subtree_layout(node_id)
        if before != self.layout_snapshot():
            self.layout_action_committed.emit("сброс смещения поддерева", before, False)

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

    def set_history_action_text(self, text: str | None) -> None:
        self._history_action_text = text.strip() if text else None
        self.update()

    def set_undo_action_label(self, label: str | None) -> None:
        # Compatibility with older screen code while the history UI migrates.
        self.set_history_action_text(f"Отменить: {label}" if label else None)

    def _menu_actions(self) -> tuple[tuple[str, str], ...]:
        actions: list[tuple[str, str]] = [
            ("make_current", "Сделать актуальной"),
            ("mark_good", "Пометить удачной"),
            ("mark_pending", "Пометить спорной"),
            ("mark_bad", "Пометить неудачной"),
            ("continue", "Продолжить от этой точки"),
        ]
        if self._history_action_text:
            actions.append(("history_toggle", self._history_action_text))
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
        return self._tree_layout().lane_offsets

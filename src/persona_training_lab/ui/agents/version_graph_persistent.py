from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF
from PySide6.QtGui import QMouseEvent

from persona_training_lab.ui.agents.version_graph_canvas_base import VersionGraphCanvas as BaseVersionGraphCanvas
from persona_training_lab.ui.viewmodels.agents import VersionNodeView


class VersionGraphCanvas(BaseVersionGraphCanvas):
    def __init__(self, nodes: tuple[VersionNodeView, ...]) -> None:
        super().__init__(nodes)
        self._layout_dirty = False
        self._layout_path = self._default_layout_path()
        self._node_offsets = self._load_offsets()
        self.update()

    def reset_layout(self) -> None:
        self._node_offsets.clear()
        self._layout_dirty = False
        self._save_offsets()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        if self._layout_dirty:
            self._save_offsets()
            self._layout_dirty = False

    def _move_nodes(self, node_ids: tuple[str, ...], delta: QPointF) -> None:
        super()._move_nodes(node_ids, delta)
        if node_ids and (delta.x() or delta.y()):
            self._layout_dirty = True

    def _default_layout_path(self) -> Path:
        return Path.home() / ".persona_training_lab" / "agents_version_graph_layout.json"

    def _load_offsets(self) -> dict[str, QPointF]:
        try:
            payload = json.loads(self._layout_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        raw_offsets = payload.get("offsets", {}) if isinstance(payload, dict) else {}
        if not isinstance(raw_offsets, dict):
            return {}
        known_ids = {node.node_id for node in self._nodes}
        offsets: dict[str, QPointF] = {}
        for node_id, value in raw_offsets.items():
            if node_id not in known_ids or not isinstance(value, dict):
                continue
            try:
                offsets[node_id] = QPointF(float(value.get("x", 0.0)), float(value.get("y", 0.0)))
            except (TypeError, ValueError):
                continue
        return offsets

    def _save_offsets(self) -> None:
        try:
            self._layout_path.parent.mkdir(parents=True, exist_ok=True)
            payload: dict[str, Any] = {
                "schema": 1,
                "offsets": {
                    node_id: {"x": point.x(), "y": point.y()}
                    for node_id, point in sorted(self._node_offsets.items())
                    if point.x() or point.y()
                },
            }
            self._layout_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            return
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any, Iterable

from persona_training_lab.ui.agents.lineage import LineageVersionNode


TONE_STATUS = {
    "good": "удачная",
    "pending": "спорная",
    "bad": "неудачная",
    "neutral": "нейтральная",
}


class LineageStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".persona_training_lab" / "agents_lineage_state.json"
        self._payload = self._load()

    def apply(self, nodes: Iterable[LineageVersionNode]) -> tuple[LineageVersionNode, ...]:
        base_nodes = list(nodes)
        overrides = self._overrides()
        current_id = self.current_node_id()
        result: list[LineageVersionNode] = []
        for node in base_nodes:
            override = overrides.get(node.node_id, {})
            branch_note = node.branch_note
            is_current = node.is_current
            if current_id:
                is_current = node.node_id == current_id
                if node.branch_note == "current" and not is_current:
                    branch_note = "main"
            tone = str(override.get("tone", node.tone))
            status = str(override.get("status", node.status))
            title = str(override.get("title", node.title))
            subtitle = str(override.get("subtitle", node.subtitle))
            result.append(
                replace(
                    node,
                    title=title,
                    subtitle=subtitle,
                    status=status,
                    tone=tone,
                    branch_note=str(override.get("branch_note", branch_note)),
                    is_current=is_current,
                )
            )
        result.extend(self._custom_nodes(result, current_id))
        return tuple(result)

    def current_node_id(self) -> str:
        current = self._payload.get("current_node_id", "")
        return str(current) if current else ""

    def set_current(self, node_id: str) -> None:
        self._payload["current_node_id"] = node_id
        self._save()

    def set_tone(self, node_id: str, tone: str) -> None:
        if tone not in TONE_STATUS:
            tone = "neutral"
        overrides = self._overrides()
        item = dict(overrides.get(node_id, {}))
        item["tone"] = tone
        item["status"] = TONE_STATUS[tone]
        overrides[node_id] = item
        self._payload["overrides"] = overrides
        self._save()

    def continue_from(self, parent_id: str) -> str:
        custom_nodes = self._payload.setdefault("custom_nodes", [])
        if not isinstance(custom_nodes, list):
            custom_nodes = []
            self._payload["custom_nodes"] = custom_nodes
        index = self._next_custom_index(custom_nodes)
        node_id = f"branch_{index:03d}"
        custom_nodes.append(
            {
                "node_id": node_id,
                "parent_id": parent_id,
                "title": f"Version · branch {index:03d}",
                "subtitle": "Новая локальная ветка от выбранной точки. Пока не связана с training run.",
                "status": "черновик",
                "tone": "pending",
                "branch_note": "side",
            }
        )
        self._save()
        return node_id

    def node_state_label(self, node_id: str) -> str:
        for node in self._payload.get("custom_nodes", []) if isinstance(self._payload.get("custom_nodes"), list) else []:
            if isinstance(node, dict) and node.get("node_id") == node_id:
                return str(node.get("status", "черновик"))
        override = self._overrides().get(node_id, {})
        status = override.get("status")
        return str(status) if status else "из источника"

    def is_custom_node(self, node_id: str) -> bool:
        custom_nodes = self._payload.get("custom_nodes", [])
        return any(isinstance(node, dict) and node.get("node_id") == node_id for node in custom_nodes if isinstance(custom_nodes, list))

    def _custom_nodes(self, existing: list[LineageVersionNode], current_id: str) -> tuple[LineageVersionNode, ...]:
        by_id = {node.node_id: node for node in existing}
        custom_nodes = self._payload.get("custom_nodes", [])
        if not isinstance(custom_nodes, list):
            return ()
        result: list[LineageVersionNode] = []
        for raw in custom_nodes:
            if not isinstance(raw, dict):
                continue
            node_id = str(raw.get("node_id", ""))
            parent_id = str(raw.get("parent_id", "")) or None
            if not node_id or node_id in by_id:
                continue
            parent_level = by_id[parent_id].level if parent_id in by_id else 0
            node = LineageVersionNode(
                node_id=node_id,
                parent_id=parent_id,
                title=str(raw.get("title", node_id)),
                subtitle=str(raw.get("subtitle", "Локальная ветка.")),
                status=str(raw.get("status", "черновик")),
                tone=str(raw.get("tone", "pending")),
                branch_note=str(raw.get("branch_note", "side")),
                is_current=node_id == current_id,
                level=int(raw.get("level", parent_level + 1)),
            )
            result.append(node)
            by_id[node_id] = node
        return tuple(result)

    def _overrides(self) -> dict[str, dict[str, Any]]:
        overrides = self._payload.setdefault("overrides", {})
        if not isinstance(overrides, dict):
            overrides = {}
            self._payload["overrides"] = overrides
        return overrides

    def _next_custom_index(self, custom_nodes: list[Any]) -> int:
        max_index = 0
        for node in custom_nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("node_id", ""))
            if not node_id.startswith("branch_"):
                continue
            try:
                max_index = max(max_index, int(node_id.removeprefix("branch_")))
            except ValueError:
                continue
        return max_index + 1

    def _load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema": 1, "overrides": {}, "custom_nodes": []}
        return payload if isinstance(payload, dict) else {"schema": 1, "overrides": {}, "custom_nodes": []}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._payload["schema"] = 1
            self._path.write_text(json.dumps(self._payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            return

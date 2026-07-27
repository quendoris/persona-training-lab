from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
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
HISTORY_LIMIT = 50


@dataclass(frozen=True, slots=True)
class HistoryTransition:
    label: str
    direction: str
    layout_snapshot: dict[str, Any]


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
            if bool(override.get("archived", False)):
                tone = "neutral"
                status = "архивная"
            result.append(
                replace(
                    node,
                    title=str(override.get("title", node.title)),
                    subtitle=str(override.get("subtitle", node.subtitle)),
                    status=status,
                    tone=tone,
                    branch_note=str(override.get("branch_note", branch_note)),
                    is_current=is_current,
                )
            )
        result.extend(self._custom_nodes(result, current_id, overrides))
        return tuple(result)

    def current_node_id(self) -> str:
        current = self._payload.get("current_node_id", "")
        return str(current) if current else ""

    def set_current(self, node_id: str, layout_snapshot: dict[str, Any] | None = None) -> None:
        if self.current_node_id() == node_id:
            return
        self._record_history("смена актуальной версии", layout_snapshot)
        self._payload["current_node_id"] = node_id
        self._save()

    def set_tone(self, node_id: str, tone: str, layout_snapshot: dict[str, Any] | None = None) -> None:
        if tone not in TONE_STATUS:
            tone = "neutral"
        overrides = self._overrides()
        existing = overrides.get(node_id, {})
        if existing.get("tone") == tone and existing.get("status") == TONE_STATUS[tone]:
            return
        self._record_history("изменение статуса", layout_snapshot)
        item = dict(overrides.get(node_id, {}))
        item["tone"] = tone
        item["status"] = TONE_STATUS[tone]
        overrides[node_id] = item
        self._payload["overrides"] = overrides
        self._save()

    def continue_from(self, parent_id: str, layout_snapshot: dict[str, Any] | None = None) -> str:
        custom_nodes = self._custom_node_payloads()
        index = self._next_custom_index(custom_nodes)
        node_id = f"branch_{index:03d}"
        self._record_history("создание ветки", layout_snapshot)
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
        self._payload["custom_nodes"] = custom_nodes
        self._save()
        return node_id

    def rename_node(self, node_id: str, title: str, layout_snapshot: dict[str, Any] | None = None) -> bool:
        clean_title = title.strip()
        if not clean_title or not self.is_custom_node(node_id):
            return False
        for raw in self._custom_node_payloads():
            if str(raw.get("node_id", "")) != node_id:
                continue
            if str(raw.get("title", "")) == clean_title:
                return True
            self._record_history("переименование ветки", layout_snapshot)
            raw["title"] = clean_title
            override = self._overrides().get(node_id)
            if isinstance(override, dict):
                override.pop("title", None)
            self._save()
            return True
        return False

    def is_archived(self, node_id: str) -> bool:
        override = self._overrides().get(node_id, {})
        return bool(override.get("archived", False))

    def set_archived(self, node_id: str, archived: bool, layout_snapshot: dict[str, Any] | None = None) -> bool:
        subtree_ids = self.custom_subtree_ids(node_id)
        if not subtree_ids:
            return False
        if all(self.is_archived(target_id) == archived for target_id in subtree_ids):
            return True
        self._record_history("архивация ветки" if archived else "возврат ветки из архива", layout_snapshot)
        overrides = self._overrides()
        for target_id in subtree_ids:
            item = dict(overrides.get(target_id, {}))
            if archived:
                item["archived"] = True
            else:
                item.pop("archived", None)
            if item:
                overrides[target_id] = item
            else:
                overrides.pop(target_id, None)
        self._payload["overrides"] = overrides
        self._save()
        return True

    def custom_subtree_ids(self, node_id: str) -> tuple[str, ...]:
        if not self.is_custom_node(node_id):
            return ()
        payloads = self._custom_node_payloads()
        children: dict[str, list[str]] = {}
        for raw in payloads:
            child_id = str(raw.get("node_id", ""))
            parent_id = str(raw.get("parent_id", ""))
            if child_id and parent_id:
                children.setdefault(parent_id, []).append(child_id)
        result: list[str] = []

        def collect(current_id: str) -> None:
            if current_id in result:
                return
            result.append(current_id)
            for child_id in children.get(current_id, []):
                collect(child_id)

        collect(node_id)
        return tuple(result)

    def delete_subtree(self, node_id: str, layout_snapshot: dict[str, Any] | None = None) -> tuple[str, ...]:
        removed = self.custom_subtree_ids(node_id)
        if not removed:
            return ()
        self._record_history("удаление ветки", layout_snapshot)
        removed_ids = set(removed)
        payloads = self._custom_node_payloads()
        root = next((raw for raw in payloads if str(raw.get("node_id", "")) == node_id), None)
        fallback_id = str(root.get("parent_id", "")) if isinstance(root, dict) else ""
        self._payload["custom_nodes"] = [raw for raw in payloads if str(raw.get("node_id", "")) not in removed_ids]
        overrides = self._overrides()
        for removed_id in removed:
            overrides.pop(removed_id, None)
        if self.current_node_id() in removed_ids:
            self._payload["current_node_id"] = fallback_id
        self._save()
        return removed

    def record_layout_action(self, label: str, before_layout: dict[str, Any]) -> None:
        self._record_history(label, before_layout)
        self._save()

    def can_undo(self) -> bool:
        return bool(self._undo_stack())

    def can_redo(self) -> bool:
        return bool(self._redo_stack())

    def can_toggle_history(self) -> bool:
        return self.can_undo() or self.can_redo()

    def history_toggle_text(self) -> str:
        direction = self._quick_direction()
        if direction == "redo" and self.can_redo():
            return f"Вернуть: {self._stack_label(self._redo_stack())}"
        if self.can_undo():
            return f"Отменить: {self._stack_label(self._undo_stack())}"
        if self.can_redo():
            return f"Вернуть: {self._stack_label(self._redo_stack())}"
        return ""

    def last_action_label(self) -> str:
        text = self.history_toggle_text()
        return text.partition(": ")[2] if ": " in text else text

    def quick_toggle(self, current_layout: dict[str, Any] | None = None) -> HistoryTransition | None:
        direction = self._quick_direction()
        if direction == "redo" and self.can_redo():
            return self.redo_last_action(current_layout)
        if self.can_undo():
            return self.undo_only(current_layout)
        if self.can_redo():
            return self.redo_last_action(current_layout)
        return None

    def undo_only(self, current_layout: dict[str, Any] | None = None) -> HistoryTransition | None:
        undo_stack = self._undo_stack()
        if not undo_stack:
            return None
        entry = undo_stack.pop()
        snapshot = self._normalise_snapshot(entry.get("snapshot"))
        if snapshot is None:
            self._save()
            return None
        label = str(entry.get("label", "последнее действие"))
        redo_stack = self._redo_stack()
        redo_stack.append({"label": label, "snapshot": self._snapshot_payload(current_layout)})
        if len(redo_stack) > HISTORY_LIMIT:
            del redo_stack[:-HISTORY_LIMIT]
        layout = self._restore_snapshot(snapshot)
        self._payload["quick_direction"] = "redo"
        self._save()
        return HistoryTransition(label=label, direction="undo", layout_snapshot=layout)

    def redo_last_action(self, current_layout: dict[str, Any] | None = None) -> HistoryTransition | None:
        redo_stack = self._redo_stack()
        if not redo_stack:
            return None
        entry = redo_stack.pop()
        snapshot = self._normalise_snapshot(entry.get("snapshot"))
        if snapshot is None:
            self._save()
            return None
        label = str(entry.get("label", "последнее действие"))
        undo_stack = self._undo_stack()
        undo_stack.append({"label": label, "snapshot": self._snapshot_payload(current_layout)})
        if len(undo_stack) > HISTORY_LIMIT:
            del undo_stack[:-HISTORY_LIMIT]
        layout = self._restore_snapshot(snapshot)
        self._payload["quick_direction"] = "undo"
        self._save()
        return HistoryTransition(label=label, direction="redo", layout_snapshot=layout)

    def undo_last_action(self, current_layout: dict[str, Any] | None = None) -> str | None:
        transition = self.undo_only(current_layout)
        return transition.label if transition is not None else None

    def node_state_label(self, node_id: str) -> str:
        if self.is_archived(node_id):
            return "архивная"
        override = self._overrides().get(node_id, {})
        status = override.get("status")
        if status:
            return str(status)
        for node in self._custom_node_payloads():
            if str(node.get("node_id", "")) == node_id:
                return str(node.get("status", "черновик"))
        return "из источника"

    def is_custom_node(self, node_id: str) -> bool:
        return any(str(node.get("node_id", "")) == node_id for node in self._custom_node_payloads())

    def _custom_nodes(
        self,
        existing: list[LineageVersionNode],
        current_id: str,
        overrides: dict[str, dict[str, Any]],
    ) -> tuple[LineageVersionNode, ...]:
        by_id = {node.node_id: node for node in existing}
        result: list[LineageVersionNode] = []
        for raw in self._custom_node_payloads():
            node_id = str(raw.get("node_id", ""))
            parent_id = str(raw.get("parent_id", "")) or None
            if not node_id or node_id in by_id:
                continue
            parent_level = by_id[parent_id].level if parent_id in by_id else 0
            override = overrides.get(node_id, {})
            tone = str(override.get("tone", raw.get("tone", "pending")))
            status = str(override.get("status", raw.get("status", "черновик")))
            if bool(override.get("archived", False)):
                tone = "neutral"
                status = "архивная"
            node = LineageVersionNode(
                node_id=node_id,
                parent_id=parent_id,
                title=str(override.get("title", raw.get("title", node_id))),
                subtitle=str(override.get("subtitle", raw.get("subtitle", "Локальная ветка."))),
                status=status,
                tone=tone,
                branch_note=str(override.get("branch_note", raw.get("branch_note", "side"))),
                is_current=node_id == current_id,
                level=int(raw.get("level", parent_level + 1)),
            )
            result.append(node)
            by_id[node_id] = node
        return tuple(result)

    def _record_history(self, label: str, layout_snapshot: dict[str, Any] | None) -> None:
        undo_stack = self._undo_stack()
        undo_stack.append({"label": label, "snapshot": self._snapshot_payload(layout_snapshot)})
        if len(undo_stack) > HISTORY_LIMIT:
            del undo_stack[:-HISTORY_LIMIT]
        self._payload["redo_stack"] = []
        self._payload["quick_direction"] = "undo"

    def _snapshot_payload(self, layout_snapshot: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "lineage": {
                "current_node_id": self.current_node_id(),
                "overrides": deepcopy(self._overrides()),
                "custom_nodes": deepcopy(self._custom_node_payloads()),
            },
            "layout": deepcopy(layout_snapshot) if isinstance(layout_snapshot, dict) else {},
        }

    def _restore_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        lineage = snapshot.get("lineage", {})
        if not isinstance(lineage, dict):
            lineage = {}
        self._payload["current_node_id"] = str(lineage.get("current_node_id", ""))
        raw_overrides = lineage.get("overrides", {})
        raw_custom_nodes = lineage.get("custom_nodes", [])
        self._payload["overrides"] = deepcopy(raw_overrides) if isinstance(raw_overrides, dict) else {}
        self._payload["custom_nodes"] = deepcopy(raw_custom_nodes) if isinstance(raw_custom_nodes, list) else []
        layout = snapshot.get("layout", {})
        return deepcopy(layout) if isinstance(layout, dict) else {}

    def _normalise_snapshot(self, raw: object) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None
        if isinstance(raw.get("lineage"), dict):
            layout = raw.get("layout", {})
            return {
                "lineage": deepcopy(raw["lineage"]),
                "layout": deepcopy(layout) if isinstance(layout, dict) else {},
            }
        return {
            "lineage": {
                "current_node_id": str(raw.get("current_node_id", "")),
                "overrides": deepcopy(raw.get("overrides", {})) if isinstance(raw.get("overrides"), dict) else {},
                "custom_nodes": deepcopy(raw.get("custom_nodes", [])) if isinstance(raw.get("custom_nodes"), list) else [],
            },
            "layout": {},
        }

    def _stack_label(self, stack: list[dict[str, Any]]) -> str:
        if not stack:
            return "последнее действие"
        return str(stack[-1].get("label", "последнее действие"))

    def _quick_direction(self) -> str:
        return "redo" if self._payload.get("quick_direction") == "redo" else "undo"

    def _undo_stack(self) -> list[dict[str, Any]]:
        return self._stack("undo_stack")

    def _redo_stack(self) -> list[dict[str, Any]]:
        return self._stack("redo_stack")

    def _stack(self, name: str) -> list[dict[str, Any]]:
        stack = self._payload.setdefault(name, [])
        if not isinstance(stack, list):
            stack = []
        cleaned = [entry for entry in stack if isinstance(entry, dict)]
        self._payload[name] = cleaned
        return cleaned

    def _custom_node_payloads(self) -> list[dict[str, Any]]:
        custom_nodes = self._payload.setdefault("custom_nodes", [])
        if not isinstance(custom_nodes, list):
            custom_nodes = []
            self._payload["custom_nodes"] = custom_nodes
        return [node for node in custom_nodes if isinstance(node, dict)]

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
        default = {
            "schema": 4,
            "overrides": {},
            "custom_nodes": [],
            "undo_stack": [],
            "redo_stack": [],
            "quick_direction": "undo",
        }
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        if "undo_stack" not in payload:
            legacy_history = payload.pop("history", [])
            payload["undo_stack"] = legacy_history if isinstance(legacy_history, list) else []
        payload.setdefault("redo_stack", [])
        payload.setdefault("quick_direction", "undo")
        payload.setdefault("overrides", {})
        payload.setdefault("custom_nodes", [])
        payload["schema"] = 4
        return payload

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._payload["schema"] = 4
            self._path.write_text(json.dumps(self._payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            return

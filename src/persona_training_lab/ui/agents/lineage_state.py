from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import json
from pathlib import Path
import re
from typing import Any, Iterable

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.agents.lineage import LineageVersionNode
from persona_training_lab.ui.i18n.text import (
    render_user_message,
    text as localized_text,
)


TONE_STATUS = {
    "good": "good",
    "pending": "pending",
    "bad": "bad",
    "neutral": "neutral",
}
HISTORY_ACTION_KEYS = {
    "make_current": "agents.history.action.make_current",
    "tone_change": "agents.history.action.tone_change",
    "branch_create": "agents.history.action.branch_create",
    "branch_rename": "agents.history.action.branch_rename",
    "branch_archive": "agents.history.action.branch_archive",
    "branch_unarchive": "agents.history.action.branch_unarchive",
    "branch_delete": "agents.history.action.branch_delete",
    "layout_move_node": "agents.history.action.layout_move_node",
    "layout_move_subtree": "agents.history.action.layout_move_subtree",
    "layout_move_mixed": "agents.history.action.layout_move_mixed",
    "layout_reset_all": "agents.history.action.layout_reset_all",
    "layout_reset_node": "agents.history.action.layout_reset_node",
    "layout_reset_subtree": "agents.history.action.layout_reset_subtree",
    "last_action": "agents.history.action.last_action",
}
RECENT_HISTORY_LIMIT = 50
CRITICAL_HISTORY_RESERVE = 20
TOTAL_HISTORY_LIMIT = RECENT_HISTORY_LIMIT + CRITICAL_HISTORY_RESERVE
_SCHEMA_VERSION = 6
_DEFAULT_BRANCH_TITLE_RE = re.compile(r"^Version · branch (?P<index>\d{3})$")


@dataclass(frozen=True, slots=True)
class HistoryTransition:
    action_code: str
    direction: str
    layout_snapshot: dict[str, Any]
    critical: bool = False

    @property
    def label(self) -> str:
        """Base-locale compatibility label for historical callers."""

        return _compat_history_label(self.action_code)


class LineageStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = (
            path
            or Path.home()
            / ".persona_training_lab"
            / "agents_lineage_state.json"
        )
        self._payload = self._load()

    def apply(
        self,
        nodes: Iterable[LineageVersionNode],
    ) -> tuple[LineageVersionNode, ...]:
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
            status_code = str(override.get("status_code", ""))
            status = (
                _status_message(status_code)
                if status_code
                else node.status
            )
            if bool(override.get("archived", False)):
                tone = "neutral"
                status = _status_message("archived")
            result.append(
                replace(
                    node,
                    title=override.get("title", node.title),
                    status=status,
                    tone=tone,
                    branch_note=str(
                        override.get("branch_note", branch_note)
                    ),
                    is_current=is_current,
                )
            )
        result.extend(
            self._custom_nodes(
                result,
                current_id,
                overrides,
            )
        )
        return tuple(result)

    def current_node_id(self) -> str:
        current = self._payload.get("current_node_id", "")
        return str(current) if current else ""

    def set_current(
        self,
        node_id: str,
        layout_snapshot: dict[str, Any] | None = None,
    ) -> None:
        if self.current_node_id() == node_id:
            return
        self._record_history("make_current", layout_snapshot)
        self._payload["current_node_id"] = node_id
        self._save()

    def set_tone(
        self,
        node_id: str,
        tone: str,
        layout_snapshot: dict[str, Any] | None = None,
    ) -> None:
        if tone not in TONE_STATUS:
            tone = "neutral"
        status_code = TONE_STATUS[tone]
        overrides = self._overrides()
        existing = overrides.get(node_id, {})
        if (
            existing.get("tone") == tone
            and existing.get("status_code") == status_code
        ):
            return
        self._record_history("tone_change", layout_snapshot)
        item = dict(overrides.get(node_id, {}))
        item["tone"] = tone
        item["status_code"] = status_code
        overrides[node_id] = item
        self._payload["overrides"] = overrides
        self._save()

    def continue_from(
        self,
        parent_id: str,
        layout_snapshot: dict[str, Any] | None = None,
    ) -> str:
        custom_nodes = self._custom_node_payloads()
        index = self._next_custom_index(custom_nodes)
        node_id = f"branch_{index:03d}"
        self._record_history("branch_create", layout_snapshot)
        custom_nodes.append(
            {
                "node_id": node_id,
                "parent_id": parent_id,
                "default_index": index,
                "status_code": "draft",
                "tone": "pending",
                "branch_note": "side",
            }
        )
        self._payload["custom_nodes"] = custom_nodes
        self._save()
        return node_id

    def rename_node(
        self,
        node_id: str,
        title: str,
        layout_snapshot: dict[str, Any] | None = None,
    ) -> bool:
        clean_title = title.strip()
        if not clean_title or not self.is_custom_node(node_id):
            return False
        current = next(
            (
                raw
                for raw in self._custom_node_payloads()
                if str(raw.get("node_id", "")) == node_id
            ),
            None,
        )
        if current is None:
            return False
        if str(current.get("title", "")) == clean_title:
            return True

        self._record_history("branch_rename", layout_snapshot)
        current = next(
            (
                raw
                for raw in self._custom_node_payloads()
                if str(raw.get("node_id", "")) == node_id
            ),
            None,
        )
        if current is None:
            raise RuntimeError(
                "Custom lineage node disappeared while recording rename history"
            )
        current["title"] = clean_title
        override = self._overrides().get(node_id)
        if isinstance(override, dict):
            override.pop("title", None)
        self._save()
        return True

    def is_archived(self, node_id: str) -> bool:
        override = self._overrides().get(node_id, {})
        return bool(override.get("archived", False))

    def set_archived(
        self,
        node_id: str,
        archived: bool,
        layout_snapshot: dict[str, Any] | None = None,
    ) -> bool:
        subtree_ids = self.custom_subtree_ids(node_id)
        if not subtree_ids:
            return False
        if all(
            self.is_archived(target_id) == archived
            for target_id in subtree_ids
        ):
            return True
        self._record_history(
            "branch_archive" if archived else "branch_unarchive",
            layout_snapshot,
        )
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

    def delete_subtree(
        self,
        node_id: str,
        layout_snapshot: dict[str, Any] | None = None,
    ) -> tuple[str, ...]:
        removed = self.custom_subtree_ids(node_id)
        if not removed:
            return ()
        self._record_history(
            "branch_delete",
            layout_snapshot,
            critical=True,
        )
        removed_ids = set(removed)
        payloads = self._custom_node_payloads()
        root = next(
            (
                raw
                for raw in payloads
                if str(raw.get("node_id", "")) == node_id
            ),
            None,
        )
        fallback_id = (
            str(root.get("parent_id", ""))
            if isinstance(root, dict)
            else ""
        )
        self._payload["custom_nodes"] = [
            raw
            for raw in payloads
            if str(raw.get("node_id", "")) not in removed_ids
        ]
        overrides = self._overrides()
        for removed_id in removed:
            overrides.pop(removed_id, None)
        if self.current_node_id() in removed_ids:
            self._payload["current_node_id"] = fallback_id
        self._save()
        return removed

    def record_layout_action(
        self,
        action_code: str,
        before_layout: dict[str, Any],
        critical: bool = False,
    ) -> None:
        self._record_history(
            action_code,
            before_layout,
            critical=critical,
        )
        self._save()

    def can_undo(self) -> bool:
        return bool(self._undo_stack())

    def can_redo(self) -> bool:
        return bool(self._redo_stack())

    def can_toggle_history(self) -> bool:
        return self.can_undo() or self.can_redo()

    def history_toggle_parts(self) -> tuple[str, str] | None:
        direction = self._quick_direction()
        if direction == "redo" and self.can_redo():
            return "redo", self._stack_action(self._redo_stack())
        if self.can_undo():
            return "undo", self._stack_action(self._undo_stack())
        if self.can_redo():
            return "redo", self._stack_action(self._redo_stack())
        return None

    def history_toggle_text(self) -> str:
        """Base-locale compatibility surface for historical callers."""

        parts = self.history_toggle_parts()
        if parts is None:
            return ""
        direction, action_code = parts
        return localized_text(
            None,
            "agents.history.redo"
            if direction == "redo"
            else "agents.history.undo",
            action=_compat_history_label(action_code),
        )

    def last_action_code(self) -> str:
        parts = self.history_toggle_parts()
        return parts[1] if parts is not None else ""

    def last_action_label(self) -> str:
        """Base-locale compatibility surface for historical callers."""

        action_code = self.last_action_code()
        return _compat_history_label(action_code) if action_code else ""

    def quick_toggle(
        self,
        current_layout: dict[str, Any] | None = None,
    ) -> HistoryTransition | None:
        direction = self._quick_direction()
        if direction == "redo" and self.can_redo():
            return self.redo_last_action(current_layout)
        if self.can_undo():
            return self.undo_only(current_layout)
        if self.can_redo():
            return self.redo_last_action(current_layout)
        return None

    def undo_only(
        self,
        current_layout: dict[str, Any] | None = None,
    ) -> HistoryTransition | None:
        undo_stack = self._undo_stack()
        if not undo_stack:
            return None
        entry = undo_stack.pop()
        snapshot = self._normalise_snapshot(entry.get("snapshot"))
        if snapshot is None:
            self._save()
            return None
        action_code = self._entry_action_code(entry)
        critical = bool(entry.get("critical", False))
        redo_stack = self._redo_stack()
        redo_stack.append(
            {
                "action_code": action_code,
                "critical": critical,
                "snapshot": self._snapshot_payload(current_layout),
            }
        )
        self._trim_redo_stack(redo_stack)
        layout = self._restore_snapshot(snapshot)
        self._payload["quick_direction"] = "redo"
        self._save()
        return HistoryTransition(
            action_code=action_code,
            direction="undo",
            layout_snapshot=layout,
            critical=critical,
        )

    def redo_last_action(
        self,
        current_layout: dict[str, Any] | None = None,
    ) -> HistoryTransition | None:
        redo_stack = self._redo_stack()
        if not redo_stack:
            return None
        entry = redo_stack.pop()
        snapshot = self._normalise_snapshot(entry.get("snapshot"))
        if snapshot is None:
            self._save()
            return None
        action_code = self._entry_action_code(entry)
        critical = bool(entry.get("critical", False))
        undo_stack = self._undo_stack()
        undo_stack.append(
            {
                "action_code": action_code,
                "critical": critical,
                "snapshot": self._snapshot_payload(current_layout),
            }
        )
        self._trim_undo_stack(undo_stack)
        layout = self._restore_snapshot(snapshot)
        self._payload["quick_direction"] = "undo"
        self._save()
        return HistoryTransition(
            action_code=action_code,
            direction="redo",
            layout_snapshot=layout,
            critical=critical,
        )

    def undo_last_action(
        self,
        current_layout: dict[str, Any] | None = None,
    ) -> str | None:
        transition = self.undo_only(current_layout)
        return transition.label if transition is not None else None

    def node_state_message(self, node_id: str) -> UserMessage:
        if self.is_archived(node_id):
            return _status_message("archived")
        override = self._overrides().get(node_id, {})
        status_code = str(override.get("status_code", ""))
        if status_code:
            return _status_message(status_code)
        for node in self._custom_node_payloads():
            if str(node.get("node_id", "")) == node_id:
                return _status_message(
                    str(node.get("status_code", "draft"))
                )
        return _status_message("source")

    def node_state_label(self, node_id: str) -> str:
        """Base-locale compatibility surface for historical callers."""

        return render_user_message(None, self.node_state_message(node_id))

    def is_custom_node(self, node_id: str) -> bool:
        return any(
            str(node.get("node_id", "")) == node_id
            for node in self._custom_node_payloads()
        )

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
            parent_level = (
                by_id[parent_id].level
                if parent_id in by_id
                else 0
            )
            override = overrides.get(node_id, {})
            tone = str(
                override.get(
                    "tone",
                    raw.get("tone", "pending"),
                )
            )
            status_code = str(
                override.get(
                    "status_code",
                    raw.get("status_code", "draft"),
                )
            )
            status = _status_message(status_code)
            if bool(override.get("archived", False)):
                tone = "neutral"
                status = _status_message("archived")
            title = override.get("title") or raw.get("title")
            if not isinstance(title, str) or not title.strip():
                index = int(
                    raw.get(
                        "default_index",
                        self._branch_index(node_id),
                    )
                )
                title = UserMessage(
                    "agents.node.custom.title",
                    {"index": f"{index:03d}"},
                )
            node = LineageVersionNode(
                node_id=node_id,
                parent_id=parent_id,
                title=title,
                subtitle=UserMessage("agents.node.custom.subtitle"),
                status=status,
                tone=tone,
                branch_note=str(
                    override.get(
                        "branch_note",
                        raw.get("branch_note", "side"),
                    )
                ),
                is_current=node_id == current_id,
                level=int(raw.get("level", parent_level + 1)),
            )
            result.append(node)
            by_id[node_id] = node
        return tuple(result)

    def _record_history(
        self,
        action_code: str,
        layout_snapshot: dict[str, Any] | None,
        critical: bool = False,
    ) -> None:
        undo_stack = self._undo_stack()
        undo_stack.append(
            {
                "action_code": action_code,
                "critical": critical,
                "snapshot": self._snapshot_payload(layout_snapshot),
            }
        )
        self._trim_undo_stack(undo_stack)
        self._payload["redo_stack"] = []
        self._payload["quick_direction"] = "undo"

    def _trim_undo_stack(
        self,
        stack: list[dict[str, Any]],
    ) -> None:
        if len(stack) <= TOTAL_HISTORY_LIMIT:
            return
        recent = stack[-RECENT_HISTORY_LIMIT:]
        older = stack[:-RECENT_HISTORY_LIMIT]
        protected = [
            entry
            for entry in older
            if bool(entry.get("critical", False))
        ]
        stack[:] = (
            protected[-CRITICAL_HISTORY_RESERVE:]
            + recent
        )

    def _trim_redo_stack(
        self,
        stack: list[dict[str, Any]],
    ) -> None:
        if len(stack) > TOTAL_HISTORY_LIMIT:
            del stack[:-TOTAL_HISTORY_LIMIT]

    def _snapshot_payload(
        self,
        layout_snapshot: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "lineage": {
                "current_node_id": self.current_node_id(),
                "overrides": deepcopy(self._overrides()),
                "custom_nodes": deepcopy(
                    self._custom_node_payloads()
                ),
            },
            "layout": (
                deepcopy(layout_snapshot)
                if isinstance(layout_snapshot, dict)
                else {}
            ),
        }

    def _restore_snapshot(
        self,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        lineage = self._normalise_lineage_payload(
            snapshot.get("lineage", {})
        )
        self._payload["current_node_id"] = str(
            lineage.get("current_node_id", "")
        )
        self._payload["overrides"] = deepcopy(
            lineage.get("overrides", {})
        )
        self._payload["custom_nodes"] = deepcopy(
            lineage.get("custom_nodes", [])
        )
        layout = snapshot.get("layout", {})
        return (
            deepcopy(layout)
            if isinstance(layout, dict)
            else {}
        )

    def _normalise_snapshot(
        self,
        raw: object,
    ) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None
        if isinstance(raw.get("lineage"), dict):
            layout = raw.get("layout", {})
            return {
                "lineage": self._normalise_lineage_payload(
                    raw["lineage"]
                ),
                "layout": (
                    deepcopy(layout)
                    if isinstance(layout, dict)
                    else {}
                ),
            }
        return {
            "lineage": self._normalise_lineage_payload(
                {
                    "current_node_id": str(
                        raw.get("current_node_id", "")
                    ),
                    "overrides": raw.get("overrides", {}),
                    "custom_nodes": raw.get("custom_nodes", []),
                }
            ),
            "layout": {},
        }

    def _stack_action(
        self,
        stack: list[dict[str, Any]],
    ) -> str:
        if not stack:
            return "last_action"
        return self._entry_action_code(stack[-1])

    def _entry_action_code(
        self,
        entry: dict[str, Any],
    ) -> str:
        action_code = str(entry.get("action_code", "")).strip()
        if action_code:
            return action_code
        label = str(entry.get("label", "")).strip()
        return _legacy_action_code(label) if label else "last_action"

    def _quick_direction(self) -> str:
        return (
            "redo"
            if self._payload.get("quick_direction") == "redo"
            else "undo"
        )

    def _undo_stack(self) -> list[dict[str, Any]]:
        return self._stack("undo_stack")

    def _redo_stack(self) -> list[dict[str, Any]]:
        return self._stack("redo_stack")

    def _stack(self, name: str) -> list[dict[str, Any]]:
        stack = self._payload.setdefault(name, [])
        if not isinstance(stack, list):
            stack = []
        cleaned: list[dict[str, Any]] = []
        for raw in stack:
            if not isinstance(raw, dict):
                continue
            entry = dict(raw)
            entry["action_code"] = self._entry_action_code(entry)
            entry.pop("label", None)
            entry["critical"] = bool(
                entry.get("critical", False)
            )
            cleaned.append(entry)
        self._payload[name] = cleaned
        return cleaned

    def _custom_node_payloads(self) -> list[dict[str, Any]]:
        custom_nodes = self._payload.setdefault("custom_nodes", [])
        if not isinstance(custom_nodes, list):
            custom_nodes = []
            self._payload["custom_nodes"] = custom_nodes
        normalized = self._normalise_custom_nodes(custom_nodes)
        self._payload["custom_nodes"] = normalized
        return normalized

    def _overrides(self) -> dict[str, dict[str, Any]]:
        overrides = self._payload.setdefault("overrides", {})
        normalized = self._normalise_overrides(overrides)
        self._payload["overrides"] = normalized
        return normalized

    def _next_custom_index(
        self,
        custom_nodes: list[Any],
    ) -> int:
        max_index = 0
        for node in custom_nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("node_id", ""))
            if not node_id.startswith("branch_"):
                continue
            max_index = max(
                max_index,
                self._branch_index(node_id),
            )
        return max_index + 1

    @staticmethod
    def _branch_index(node_id: str) -> int:
        if not node_id.startswith("branch_"):
            return 0
        try:
            return int(node_id.removeprefix("branch_"))
        except ValueError:
            return 0

    def _load(self) -> dict[str, Any]:
        default = self._default_payload()
        try:
            payload = json.loads(
                self._path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        return self._normalise_loaded_payload(payload)

    def _normalise_loaded_payload(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = deepcopy(payload)
        source_schema = _schema_number(normalized.get("schema"))
        if source_schema < _SCHEMA_VERSION:
            self._migrate_legacy_generated_titles(normalized)
        if "undo_stack" not in normalized:
            legacy_history = normalized.pop("history", [])
            normalized["undo_stack"] = (
                legacy_history
                if isinstance(legacy_history, list)
                else []
            )
        normalized.setdefault("redo_stack", [])
        normalized.setdefault("quick_direction", "undo")
        lineage = self._normalise_lineage_payload(normalized)
        normalized["current_node_id"] = lineage[
            "current_node_id"
        ]
        normalized["overrides"] = lineage["overrides"]
        normalized["custom_nodes"] = lineage[
            "custom_nodes"
        ]
        normalized["undo_stack"] = self._normalise_history_stack(
            normalized.get("undo_stack", [])
        )
        normalized["redo_stack"] = self._normalise_history_stack(
            normalized.get("redo_stack", [])
        )
        normalized["schema"] = _SCHEMA_VERSION
        return normalized

    def _migrate_legacy_generated_titles(
        self,
        payload: dict[str, Any],
    ) -> None:
        self._strip_legacy_generated_titles(payload.get("custom_nodes"))
        for stack_name in ("history", "undo_stack", "redo_stack"):
            raw_stack = payload.get(stack_name)
            if not isinstance(raw_stack, list):
                continue
            for raw_entry in raw_stack:
                if not isinstance(raw_entry, dict):
                    continue
                snapshot = raw_entry.get("snapshot")
                if not isinstance(snapshot, dict):
                    continue
                lineage = snapshot.get("lineage")
                if isinstance(lineage, dict):
                    self._strip_legacy_generated_titles(
                        lineage.get("custom_nodes")
                    )
                else:
                    self._strip_legacy_generated_titles(
                        snapshot.get("custom_nodes")
                    )

    def _strip_legacy_generated_titles(self, raw: object) -> None:
        if not isinstance(raw, list):
            return
        for value in raw:
            if not isinstance(value, dict):
                continue
            node_id = str(value.get("node_id", ""))
            index = self._branch_index(node_id)
            title = value.get("title")
            if not isinstance(title, str):
                continue
            match = _DEFAULT_BRANCH_TITLE_RE.fullmatch(title.strip())
            if match is None:
                continue
            if int(match.group("index")) == index:
                value.pop("title", None)

    def _normalise_lineage_payload(
        self,
        raw: object,
    ) -> dict[str, Any]:
        data = raw if isinstance(raw, dict) else {}
        return {
            "current_node_id": str(
                data.get("current_node_id", "")
            ),
            "overrides": self._normalise_overrides(
                data.get("overrides", {})
            ),
            "custom_nodes": self._normalise_custom_nodes(
                data.get("custom_nodes", [])
            ),
        }

    def _normalise_overrides(
        self,
        raw: object,
    ) -> dict[str, dict[str, Any]]:
        if not isinstance(raw, dict):
            return {}
        normalized: dict[str, dict[str, Any]] = {}
        for node_id, value in raw.items():
            if not isinstance(value, dict):
                continue
            item = dict(value)
            tone = str(item.get("tone", "")).strip()
            if "status_code" not in item and item.get("status"):
                item["status_code"] = _legacy_status_code(
                    str(item.get("status", "")),
                    tone=tone,
                )
            item.pop("status", None)
            item.pop("subtitle", None)
            if item:
                normalized[str(node_id)] = item
        return normalized

    def _normalise_custom_nodes(
        self,
        raw: object,
    ) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        normalized: list[dict[str, Any]] = []
        for value in raw:
            if not isinstance(value, dict):
                continue
            item = dict(value)
            node_id = str(item.get("node_id", ""))
            if not node_id:
                continue
            tone = str(item.get("tone", "pending"))
            if "status_code" not in item:
                item["status_code"] = _legacy_status_code(
                    str(item.get("status", "")),
                    tone=tone,
                )
            item.pop("status", None)
            item.pop("subtitle", None)
            item.setdefault("default_index", self._branch_index(node_id))
            normalized.append(item)
        return normalized

    def _normalise_history_stack(
        self,
        raw: object,
    ) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        normalized: list[dict[str, Any]] = []
        for value in raw:
            if not isinstance(value, dict):
                continue
            item = dict(value)
            item["action_code"] = self._entry_action_code(item)
            item.pop("label", None)
            item["critical"] = bool(item.get("critical", False))
            snapshot = self._normalise_snapshot(item.get("snapshot"))
            if snapshot is not None:
                item["snapshot"] = snapshot
            normalized.append(item)
        return normalized

    @staticmethod
    def _default_payload() -> dict[str, Any]:
        return {
            "schema": _SCHEMA_VERSION,
            "current_node_id": "",
            "overrides": {},
            "custom_nodes": [],
            "undo_stack": [],
            "redo_stack": [],
            "quick_direction": "undo",
        }

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._payload["schema"] = _SCHEMA_VERSION
            self._path.write_text(
                json.dumps(
                    self._payload,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            return


def _schema_number(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _status_message(status_code: str) -> UserMessage:
    code = status_code if status_code else "source"
    return UserMessage(f"agents.status.{code}")


def _legacy_status_code(label: str, *, tone: str) -> str:
    clean = label.strip()
    if clean == localized_text(None, "agents.status.draft"):
        return "draft"
    if clean == localized_text(None, "agents.status.archived"):
        return "archived"
    if tone in TONE_STATUS:
        return TONE_STATUS[tone]
    return "source"


def _legacy_action_code(label: str) -> str:
    clean = label.strip()
    if not clean:
        return "last_action"
    for action_code, key in HISTORY_ACTION_KEYS.items():
        if clean == localized_text(None, key):
            return action_code
    return clean


def _compat_history_label(action_code: str) -> str:
    key = HISTORY_ACTION_KEYS.get(action_code)
    if key is None:
        return action_code
    return localized_text(None, key)

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from persona_training_lab.config.app_settings import default_workspace_dir
from persona_training_lab.ui.agents.lineage_state import (
    HistoryTransition,
    LineageStateStore,
)


class LineageStateLoadError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AtomicHistoryPreview:
    action_code: str
    direction: str
    critical: bool
    metadata: dict[str, Any]


class AtomicLineageStateStore(LineageStateStore):
    """Durable lineage state with atomic replacement and memory rollback."""

    def __init__(self, path: Path | None = None) -> None:
        self._pending_history_metadata: dict[str, Any] | None = None
        resolved_path = (
            path
            if path is not None
            else default_workspace_dir() / "agents_lineage_state.json"
        )
        super().__init__(resolved_path)
        self._persisted_payload = deepcopy(self._payload)

    def capture_transaction_state(self) -> dict[str, Any]:
        return deepcopy(self._payload)

    def restore_transaction_state(
        self,
        snapshot: dict[str, Any],
    ) -> None:
        previous_payload = deepcopy(self._payload)
        previous_persisted = deepcopy(self._persisted_payload)
        self._payload = self._normalise_loaded_payload(
            deepcopy(snapshot)
        )
        try:
            self._save()
        except Exception:
            self._payload = previous_payload
            self._persisted_payload = previous_persisted
            raise

    def stage_history_metadata(self, metadata: dict[str, Any]) -> None:
        self._pending_history_metadata = deepcopy(metadata)

    def clear_staged_history_metadata(self) -> None:
        self._pending_history_metadata = None

    def history_toggle_preview(self) -> AtomicHistoryPreview | None:
        direction = self._quick_direction()
        if direction == "redo" and self.can_redo():
            return self._preview(self._redo_stack(), "redo")
        if self.can_undo():
            return self._preview(self._undo_stack(), "undo")
        if self.can_redo():
            return self._preview(self._redo_stack(), "redo")
        return None

    def undo_preview(self) -> AtomicHistoryPreview | None:
        return self._preview(self._undo_stack(), "undo")

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
        metadata = self._history_metadata(entry)
        redo_entry: dict[str, Any] = {
            "action_code": action_code,
            "critical": critical,
            "snapshot": self._snapshot_payload(current_layout),
        }
        if metadata:
            redo_entry["metadata"] = metadata
        redo_stack = self._redo_stack()
        redo_stack.append(redo_entry)
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
        metadata = self._history_metadata(entry)
        undo_entry: dict[str, Any] = {
            "action_code": action_code,
            "critical": critical,
            "snapshot": self._snapshot_payload(current_layout),
        }
        if metadata:
            undo_entry["metadata"] = metadata
        undo_stack = self._undo_stack()
        undo_stack.append(undo_entry)
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

    def _record_history(
        self,
        action_code: str,
        layout_snapshot: dict[str, Any] | None,
        critical: bool = False,
    ) -> None:
        super()._record_history(
            action_code,
            layout_snapshot,
            critical=critical,
        )
        metadata = self._pending_history_metadata
        self._pending_history_metadata = None
        if not metadata:
            return
        undo_stack = self._undo_stack()
        if undo_stack:
            undo_stack[-1]["metadata"] = deepcopy(metadata)

    def _preview(
        self,
        stack: list[dict[str, Any]],
        direction: str,
    ) -> AtomicHistoryPreview | None:
        if not stack:
            return None
        entry = stack[-1]
        return AtomicHistoryPreview(
            action_code=self._entry_action_code(entry),
            direction=direction,
            critical=bool(entry.get("critical", False)),
            metadata=self._history_metadata(entry),
        )

    @staticmethod
    def _history_metadata(entry: dict[str, Any]) -> dict[str, Any]:
        metadata = entry.get("metadata")
        return deepcopy(metadata) if isinstance(metadata, dict) else {}

    def _load(self) -> dict[str, Any]:
        try:
            raw_text = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return self._default_payload()
        except OSError as error:
            raise LineageStateLoadError(
                f"Cannot read lineage state {self._path}: {error}"
            ) from error

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as error:
            raise LineageStateLoadError(
                f"Lineage state is not valid JSON: {self._path}"
            ) from error
        if not isinstance(payload, dict):
            raise LineageStateLoadError(
                f"Lineage state root must be an object: {self._path}"
            )
        return self._normalise_loaded_payload(payload)

    def _save(self) -> None:
        payload = deepcopy(self._payload)
        path = self._path
        temporary_path: Path | None = None

        try:
            serialized = json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(serialized)
                temporary.flush()
                os.fsync(temporary.fileno())

            os.replace(temporary_path, path)
            temporary_path = None
        except Exception:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
            self._payload = deepcopy(self._persisted_payload)
            raise

        self._persisted_payload = payload
        self._fsync_directory(path.parent)

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        try:
            descriptor = os.open(directory, flags)
        except OSError:
            return
        try:
            try:
                os.fsync(descriptor)
            except OSError:
                pass
        finally:
            try:
                os.close(descriptor)
            except OSError:
                pass


__all__ = (
    "AtomicHistoryPreview",
    "AtomicLineageStateStore",
    "LineageStateLoadError",
)

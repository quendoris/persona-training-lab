from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from persona_training_lab.ui.agents.lineage_state import LineageStateStore


class LineageStateLoadError(RuntimeError):
    pass


class AtomicLineageStateStore(LineageStateStore):
    """Durable lineage state with atomic replacement and memory rollback."""

    def __init__(self, path: Path | None = None) -> None:
        super().__init__(path)
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


__all__ = ("AtomicLineageStateStore", "LineageStateLoadError")

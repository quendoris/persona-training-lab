from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLockFile


class WorkspaceAlreadyOpenError(RuntimeError):
    """Raised when another PTL process already owns the workspace."""


class WorkspaceOwnership:
    """Hold one cross-process writer lease for a mutable PTL workspace."""

    LOCK_FILENAME = ".ptl-workspace.lock"

    def __init__(self, workspace_root: Path) -> None:
        root = workspace_root.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._lock_path = root / self.LOCK_FILENAME
        self._lock = QLockFile(str(self._lock_path))
        self._acquired = False

    @property
    def lock_path(self) -> Path:
        return self._lock_path

    @property
    def acquired(self) -> bool:
        return self._acquired

    def acquire(self) -> None:
        if self._acquired:
            return
        if not self._lock.tryLock(0):
            raise WorkspaceAlreadyOpenError(
                "Persona Training Lab workspace is already open for writing: "
                f"{self._lock_path.parent}"
            )
        self._acquired = True

    def release(self) -> None:
        if not self._acquired:
            return
        self._lock.unlock()
        self._acquired = False


__all__ = ("WorkspaceAlreadyOpenError", "WorkspaceOwnership")

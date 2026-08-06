from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtWidgets import QMainWindow


@dataclass(frozen=True, slots=True)
class WindowRestoreResult:
    geometry_restored: bool
    docks_restored: bool
    workspace_key: str

    @property
    def any_restored(self) -> bool:
        return self.geometry_restored or self.docks_restored


class WindowStateStore:
    """Persist the desktop shell without coupling it to a concrete window."""

    GEOMETRY_KEY = "shell/window_geometry"
    DOCK_STATE_KEY = "shell/dock_state"
    WORKSPACE_KEY = "shell/current_workspace"
    STATE_VERSION = 2

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings()

    def restore(self, window: QMainWindow) -> WindowRestoreResult:
        geometry = self._as_byte_array(self._settings.value(self.GEOMETRY_KEY))
        dock_state = self._as_byte_array(self._settings.value(self.DOCK_STATE_KEY))
        workspace_key = str(self._settings.value(self.WORKSPACE_KEY, "") or "")

        geometry_restored = False
        docks_restored = False
        if geometry is not None and not geometry.isEmpty():
            geometry_restored = bool(window.restoreGeometry(geometry))
        if dock_state is not None and not dock_state.isEmpty():
            docks_restored = bool(
                window.restoreState(dock_state, self.STATE_VERSION)
            )

        return WindowRestoreResult(
            geometry_restored=geometry_restored,
            docks_restored=docks_restored,
            workspace_key=workspace_key,
        )

    def save(self, window: QMainWindow, workspace_key: str) -> bool:
        self._settings.setValue(self.GEOMETRY_KEY, window.saveGeometry())
        self._settings.setValue(
            self.DOCK_STATE_KEY,
            window.saveState(self.STATE_VERSION),
        )
        self._settings.setValue(self.WORKSPACE_KEY, workspace_key)
        self._settings.sync()
        return self._settings.status() == QSettings.Status.NoError

    def clear(self) -> None:
        for key in (
            self.GEOMETRY_KEY,
            self.DOCK_STATE_KEY,
            self.WORKSPACE_KEY,
        ):
            self._settings.remove(key)
        self._settings.sync()

    @staticmethod
    def _as_byte_array(value: object) -> QByteArray | None:
        if isinstance(value, QByteArray):
            return value
        if isinstance(value, bytes):
            return QByteArray(value)
        if isinstance(value, bytearray):
            return QByteArray(bytes(value))
        return None

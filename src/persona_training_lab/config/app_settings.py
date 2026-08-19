from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


_APP_DIRNAME_POSIX = "persona-training-lab"
_APP_DIRNAME_DESKTOP = "Persona Training Lab"


def default_workspace_dir() -> Path:
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if local_app_data:
            return Path(local_app_data).expanduser() / _APP_DIRNAME_DESKTOP
        return Path.home() / "AppData" / "Local" / _APP_DIRNAME_DESKTOP

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / _APP_DIRNAME_DESKTOP

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    data_home = (
        Path(xdg_data_home).expanduser()
        if xdg_data_home
        else Path.home() / ".local" / "share"
    )
    return data_home / _APP_DIRNAME_POSIX


@dataclass(slots=True, frozen=True)
class AppSettings:
    app_name: str = "Persona Training Lab"
    organization_name: str = "ИИ чувства"
    workspace_dir: Path = field(default_factory=default_workspace_dir)
    sqlite_filename: str = "app.db"
    artifacts_dirname: str = "artifacts"
    exports_dirname: str = "exports"
    temp_dirname: str = "temp"
    cache_dirname: str = "cache"

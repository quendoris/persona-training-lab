from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class AppSettings:
    app_name: str = "Persona Training Lab"
    organization_name: str = "ИИ чувства"
    workspace_dir: Path = Path.cwd()
    sqlite_filename: str = "app.db"
    artifacts_dirname: str = "artifacts"
    exports_dirname: str = "exports"
    temp_dirname: str = "temp"
    cache_dirname: str = "cache"

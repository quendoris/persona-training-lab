from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from persona_training_lab.config.app_settings import AppSettings


@dataclass(slots=True, frozen=True)
class WorkspacePaths:
    root: Path
    sqlite_db: Path
    artifacts: Path
    exports: Path
    temp: Path
    cache: Path


def build_workspace_paths(settings: AppSettings) -> WorkspacePaths:
    root = settings.workspace_dir
    return WorkspacePaths(
        root=root,
        sqlite_db=root / settings.sqlite_filename,
        artifacts=root / settings.artifacts_dirname,
        exports=root / settings.exports_dirname,
        temp=root / settings.temp_dirname,
        cache=root / settings.cache_dirname,
    )


def ensure_workspace_dirs(paths: WorkspacePaths) -> None:
    for directory in [paths.root, paths.artifacts, paths.exports, paths.temp, paths.cache]:
        directory.mkdir(parents=True, exist_ok=True)

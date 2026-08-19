from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from persona_training_lab.application.local_model.service import LocalModelService
import persona_training_lab.config.app_settings as app_settings_module
from persona_training_lab.config.app_settings import AppSettings, default_workspace_dir
from persona_training_lab.config.paths import build_workspace_paths
from persona_training_lab.ui.agents.lineage_state_atomic import (
    AtomicLineageStateStore,
)


def test_default_workspace_is_independent_from_current_working_directory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    cwd = tmp_path / "cwd"
    xdg_data_home = tmp_path / "xdg-data"
    cwd.mkdir()

    monkeypatch.chdir(cwd)
    monkeypatch.setattr(app_settings_module.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))

    settings = AppSettings()
    paths = build_workspace_paths(settings)

    expected_root = xdg_data_home / "persona-training-lab"
    assert settings.workspace_dir == expected_root
    assert settings.workspace_dir != cwd
    assert paths.root == expected_root
    assert paths.sqlite_db == expected_root / "app.db"


def test_default_agents_lineage_state_path_is_workspace_stable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    cwd = tmp_path / "cwd"
    xdg_data_home = tmp_path / "xdg-data"
    cwd.mkdir()

    monkeypatch.chdir(cwd)
    monkeypatch.setattr(app_settings_module.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))

    store = AtomicLineageStateStore()

    expected = (
        xdg_data_home
        / "persona-training-lab"
        / "agents_lineage_state.json"
    )
    assert store._path == expected
    assert store._path.parent != cwd
    assert store._path.parent == default_workspace_dir()


def test_default_local_model_path_is_workspace_stable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    cwd = tmp_path / "cwd"
    xdg_data_home = tmp_path / "xdg-data"
    cwd.mkdir()

    monkeypatch.chdir(cwd)
    monkeypatch.setattr(app_settings_module.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data_home))

    service = LocalModelService(probe_provider=cast(Any, object()))

    expected = xdg_data_home / "persona-training-lab" / "models" / "qwen3.5-0.8b"
    assert Path(service.model_path) == expected
    assert Path(service.model_path).parent.parent != cwd


def test_default_workspace_uses_windows_local_app_data(
    monkeypatch,
    tmp_path: Path,
) -> None:
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.setattr(app_settings_module.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))

    assert default_workspace_dir() == local_app_data / "Persona Training Lab"


def test_explicit_workspace_override_remains_supported(tmp_path: Path) -> None:
    custom_root = tmp_path / "custom-workspace"
    settings = AppSettings(workspace_dir=custom_root)
    paths = build_workspace_paths(settings)

    assert paths.root == custom_root
    assert paths.sqlite_db == custom_root / "app.db"
    assert paths.artifacts == custom_root / "artifacts"
    assert paths.exports == custom_root / "exports"
    assert paths.temp == custom_root / "temp"
    assert paths.cache == custom_root / "cache"

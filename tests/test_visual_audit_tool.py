from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from persona_training_lab.ui.shell.app_sidebar import NAVIGATION_KEYS


ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _run_visual_audit(tmp_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    return subprocess.run(
        (
            sys.executable,
            "tools/visual_audit.py",
            "--output",
            str(tmp_path),
            *arguments,
        ),
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _single_session(tmp_path: Path) -> Path:
    sessions = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(sessions) == 1
    return sessions[0]


def test_visual_audit_defaults_to_every_complete_locale(tmp_path: Path) -> None:
    completed = _run_visual_audit(
        tmp_path,
        "--width",
        "960",
        "--height",
        "620",
        "--settle-ms",
        "0",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    session = _single_session(tmp_path)
    manifest = json.loads((session / "manifest.json").read_text(encoding="utf-8"))

    locales = manifest["locales"]
    assert locales[0] == "ru-RU"
    assert {"ru-RU", "en-US", "es-ES"}.issubset(set(locales))
    assert manifest["failures"] == []
    assert len(manifest["captures"]) == len(NAVIGATION_KEYS) * len(locales)
    assert {item["locale"] for item in manifest["captures"]} == set(locales)


def test_visual_audit_captures_every_route_in_real_offscreen_app(tmp_path: Path) -> None:
    completed = _run_visual_audit(
        tmp_path,
        "--locale",
        "ru-RU",
        "--width",
        "960",
        "--height",
        "620",
        "--settle-ms",
        "0",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    session = _single_session(tmp_path)

    manifest = json.loads((session / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "ptl:visual-audit:v1"
    assert manifest["mode"] == "automatic"
    assert manifest["locales"] == ["ru-RU"]
    assert manifest["routes"] == list(NAVIGATION_KEYS)
    assert manifest["window"] == {"width": 960, "height": 620}
    assert manifest["failures"] == []
    assert len(manifest["captures"]) == len(NAVIGATION_KEYS)
    assert all(item["width"] == 960 for item in manifest["captures"])
    assert all(item["height"] == 620 for item in manifest["captures"])

    expected_files = {
        f"screenshots/ru-RU__{route}.png"
        for route in NAVIGATION_KEYS
    }
    captured_files = {item["file"] for item in manifest["captures"]}
    assert captured_files == expected_files
    for relative_path in expected_files:
        image = session / relative_path
        assert image.read_bytes().startswith(PNG_SIGNATURE)

    bundle = session / "visual-audit.zip"
    assert bundle.is_file()
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
    assert {"manifest.json", "summary.txt", *expected_files}.issubset(names)


def test_interactive_visual_audit_records_current_top_level_state(tmp_path: Path) -> None:
    completed = _run_visual_audit(
        tmp_path,
        "--interactive",
        "--capture-on-start",
        "--exit-after-captures",
        "1",
        "--locale",
        "ru-RU",
        "--width",
        "960",
        "--height",
        "620",
        "--settle-ms",
        "0",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    session = _single_session(tmp_path)
    manifest = json.loads((session / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "ptl:visual-audit:v1"
    assert manifest["mode"] == "interactive"
    assert manifest["capture_hotkey"] == "F12"
    assert manifest["failures"] == []
    assert len(manifest["captures"]) == 1

    capture = manifest["captures"][0]
    assert capture["locale"] == "ru-RU"
    assert capture["route"] in NAVIGATION_KEYS
    assert capture["width"] >= 960
    assert capture["height"] >= 620
    assert capture["windows"]

    expected_files = {capture["state_file"]}
    for window in capture["windows"]:
        expected_files.add(window["file"])
        image = session / window["file"]
        assert image.read_bytes().startswith(PNG_SIGNATURE)
        assert window["width"] > 0
        assert window["height"] > 0

    for relative_path in expected_files:
        assert (session / relative_path).is_file()

    bundle = session / "visual-audit.zip"
    assert bundle.is_file()
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
    assert {"manifest.json", "summary.txt", *expected_files}.issubset(names)


def test_visual_audit_build_window_isolates_workspace_and_user_settings(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "audit-workspace"
    script = """
from pathlib import Path
import json
import sys

from tools.visual_audit import _build_window, _shutdown_window

workspace = Path(sys.argv[1])
app, window, _localization = _build_window(
    workspace_root=workspace,
    scale="0.90",
    theme="velvet",
    accent="cyan",
    initial_locale="ru-RU",
)
try:
    agents = window._workspace.workspace("agents")
    training = window._workspace.workspace("training")
    payload = {
        "agents_state": str(agents._state._path),
        "key_bindings": str(window._key_binding_manager.storage_path),
        "qsettings": str(window._window_state_store._settings.fileName()),
        "model_path": str(training._vm.local_model_path),
    }
    print(json.dumps(payload))
finally:
    _shutdown_window(app, window)
"""
    environment = dict(os.environ)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-c", script, str(workspace)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    resolved = workspace.resolve()
    assert Path(payload["agents_state"]) == resolved / "agents_lineage_state.json"
    assert Path(payload["key_bindings"]) == (
        resolved / "visual_audit_key_bindings.json"
    )
    assert Path(payload["qsettings"]) == resolved / "visual_audit_qsettings.ini"
    assert Path(payload["model_path"]) == resolved / "models" / "qwen3.5-0.8b"

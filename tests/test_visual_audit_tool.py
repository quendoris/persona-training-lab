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


def test_visual_audit_captures_every_route_in_real_offscreen_app(tmp_path: Path) -> None:
    environment = dict(os.environ)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        (
            sys.executable,
            "tools/visual_audit.py",
            "--output",
            str(tmp_path),
            "--locale",
            "ru-RU",
            "--width",
            "960",
            "--height",
            "620",
            "--settle-ms",
            "0",
        ),
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    sessions = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(sessions) == 1
    session = sessions[0]

    manifest = json.loads((session / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "ptl:visual-audit:v1"
    assert manifest["locales"] == ["ru-RU"]
    assert manifest["routes"] == list(NAVIGATION_KEYS)
    assert manifest["failures"] == []
    assert len(manifest["captures"]) == len(NAVIGATION_KEYS)

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

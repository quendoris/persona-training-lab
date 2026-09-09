from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "codebase_stats.py"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "ptl-tests@example.invalid")
    _git(repo, "config", "user.name", "PTL Tests")
    (repo / "sample.py").write_text("value = 1\n", encoding="utf-8")
    _git(repo, "add", "sample.py")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _run_json(repo: Path) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    assert isinstance(payload, dict)
    return payload


def test_codebase_stats_reports_exact_clean_repository_identity(tmp_path) -> None:
    repo = _repo(tmp_path)

    payload = _run_json(repo)

    commit = _git(repo, "rev-parse", "HEAD")
    assert payload["repository_root"] == str(repo.resolve())
    assert payload["branch"] == _git(repo, "branch", "--show-current")
    assert payload["commit_full"] == commit
    assert payload["commit"] == _git(repo, "rev-parse", "--short", "HEAD")
    assert payload["upstream"] == "(no upstream)"
    assert payload["dirty"] is False
    assert payload["tracked_dirty"] is False
    assert payload["untracked"] is False
    assert payload["dirty_paths"] == []


def test_codebase_stats_distinguishes_tracked_and_untracked_changes(tmp_path) -> None:
    repo = _repo(tmp_path)
    (repo / "sample.py").write_text("value = 2\n", encoding="utf-8")
    (repo / "scratch.txt").write_text("not tracked\n", encoding="utf-8")

    payload = _run_json(repo)

    assert payload["dirty"] is True
    assert payload["tracked_dirty"] is True
    assert payload["untracked"] is True
    dirty_paths = payload["dirty_paths"]
    assert isinstance(dirty_paths, list)
    assert any(str(line).endswith("sample.py") for line in dirty_paths)
    assert any(str(line).startswith("?? scratch.txt") for line in dirty_paths)

    files = payload["files"]
    assert isinstance(files, list)
    paths = {str(item["path"]) for item in files if isinstance(item, dict)}
    assert "sample.py" in paths
    assert "scratch.txt" not in paths

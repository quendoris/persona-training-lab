from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import tools.release_gate as release_gate_module
from tools.release_gate import ReleaseGate, _parse_args


def _gate_for_policy(*, quick: bool) -> ReleaseGate:
    gate = object.__new__(ReleaseGate)
    gate._quick = quick
    return gate


def test_full_release_profile_always_blocks_on_mypy_and_build() -> None:
    gate = _gate_for_policy(quick=False)

    setup_names = tuple(step.name for step in gate._setup_steps())
    final_names = tuple(step.name for step in gate._final_steps())

    assert setup_names == ("compileall", "ruff", "typing-audit", "mypy")
    assert final_names == ("i18n-audit", "codebase-stats", "build")
    assert all(step.blocking for step in gate._setup_steps())
    assert all(step.blocking for step in gate._final_steps())


def test_quick_release_profile_is_explicitly_smaller_than_full() -> None:
    gate = _gate_for_policy(quick=True)

    assert tuple(step.name for step in gate._setup_steps()) == (
        "compileall",
        "ruff",
        "typing-audit",
    )
    assert tuple(step.name for step in gate._final_steps()) == (
        "i18n-audit",
        "codebase-stats",
    )


@pytest.mark.parametrize(
    "removed_flag",
    ("--strict-mypy", "--skip-mypy", "--skip-build"),
)
def test_release_gate_rejects_removed_typing_and_build_bypasses(
    monkeypatch: pytest.MonkeyPatch,
    removed_flag: str,
) -> None:
    monkeypatch.setattr(sys, "argv", ["release_gate.py", removed_flag])

    with pytest.raises(SystemExit) as error:
        _parse_args()

    assert error.value.code == 2


def test_release_gate_rejects_dirty_worktree_before_report_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _dirty_metadata(_gate: ReleaseGate) -> dict[str, object]:
        return {
            "commit": "0123456789abcdef",
            "branch": "agent/history-keyguard-poller",
            "dirty": True,
            "dirty_paths": [" M src/persona_training_lab/example.py"],
        }

    monkeypatch.setattr(ReleaseGate, "_collect_metadata", _dirty_metadata)

    with pytest.raises(RuntimeError, match="clean Git worktree") as error:
        ReleaseGate(
            output_root=tmp_path,
            seed=123,
            runs=1,
            quick=True,
        )

    assert "src/persona_training_lab/example.py" in str(error.value)
    assert not tuple(tmp_path.iterdir())


def test_release_gate_metadata_requires_resolvable_git_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release_gate_module, "_git", lambda *_args: "")
    gate = object.__new__(ReleaseGate)

    with pytest.raises(RuntimeError, match="resolvable HEAD"):
        gate._collect_metadata()


def test_release_gate_source_tree_has_no_ignored_runtime_inputs() -> None:
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        (
            "git",
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--",
            "src",
            "tests",
            "tools",
        ),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert completed.returncode == 0, completed.stderr

    ignored_paths = tuple(
        Path(line.strip())
        for line in completed.stdout.splitlines()
        if line.strip()
    )
    allowed_names = {".DS_Store", "Thumbs.db"}
    unexpected = tuple(
        str(path)
        for path in ignored_paths
        if "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
        and path.name not in allowed_names
    )

    assert unexpected == (), (
        "Ignored files under src/tests/tools can alter local execution without "
        f"appearing in the recorded Git commit: {unexpected}"
    )

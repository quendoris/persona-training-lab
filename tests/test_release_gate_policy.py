from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import tools.release_gate as release_gate_module
from tools.candidate_identity_audit import audit_candidate_identity
from tools.release_gate import ReleaseGate, _parse_args, _read_release_versions


def _gate_for_policy(*, quick: bool) -> ReleaseGate:
    gate = object.__new__(ReleaseGate)
    gate._quick = quick
    gate._metadata = {"commit": "0123456789abcdef"}
    return gate


def test_full_release_profile_always_blocks_on_mypy_and_build() -> None:
    gate = _gate_for_policy(quick=False)

    setup_names = tuple(step.name for step in gate._setup_steps())
    final_names = tuple(step.name for step in gate._final_steps())

    assert setup_names == ("compileall", "ruff", "typing-audit", "mypy")
    assert final_names == (
        "i18n-audit",
        "docs-audit",
        "codebase-stats",
        "build",
        "package-audit",
        "candidate-identity",
    )
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
        "docs-audit",
        "codebase-stats",
        "candidate-identity",
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


def test_release_gate_rejects_mismatched_package_and_runtime_versions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _mismatched_metadata(_gate: ReleaseGate) -> dict[str, object]:
        return {
            "commit": "0123456789abcdef",
            "branch": "agent/history-keyguard-poller",
            "dirty": False,
            "dirty_paths": [],
            "package_version": "0.1.0",
            "runtime_version": "0.1.1",
        }

    monkeypatch.setattr(ReleaseGate, "_collect_metadata", _mismatched_metadata)

    with pytest.raises(RuntimeError, match="Release version mismatch"):
        ReleaseGate(
            output_root=tmp_path,
            seed=123,
            runs=1,
            quick=True,
        )

    assert not tuple(tmp_path.iterdir())


def test_release_version_sources_match_in_repository() -> None:
    package_version, runtime_version = _read_release_versions()

    assert package_version == "0.1.0"
    assert runtime_version == package_version


def test_release_gate_metadata_requires_resolvable_git_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release_gate_module, "_git", lambda *_args: "")
    gate = object.__new__(ReleaseGate)

    with pytest.raises(RuntimeError, match="resolvable HEAD"):
        gate._collect_metadata()


def test_release_build_output_is_repository_ignored() -> None:
    root = Path(__file__).resolve().parents[1]
    ignore_rules = (root / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/dist/" in {line.strip() for line in ignore_rules}


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


def test_production_model_loaders_do_not_enable_remote_code() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "persona_training_lab"
    offenders: list[str] = []

    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if (
                    keyword.arg == "trust_remote_code"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    offenders.append(f"{path.relative_to(root.parent.parent)}:{node.lineno}")

    assert offenders == [], (
        "Production model loading must not execute repository-supplied Python via "
        f"trust_remote_code=True: {offenders}"
    )



def test_candidate_identity_audit_detects_worktree_change(
    tmp_path: Path,
) -> None:
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    subprocess.run(
        ("git", "config", "user.email", "ptl-test@example.invalid"),
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ("git", "config", "user.name", "PTL Test"),
        cwd=tmp_path,
        check=True,
    )
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("stable\n", encoding="utf-8")
    subprocess.run(("git", "add", "tracked.txt"), cwd=tmp_path, check=True)
    subprocess.run(
        ("git", "commit", "-qm", "seed"),
        cwd=tmp_path,
        check=True,
    )
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert audit_candidate_identity(tmp_path, head)["passed"] is True

    tracked.write_text("changed during gate\n", encoding="utf-8")
    payload = audit_candidate_identity(tmp_path, head)

    assert payload["passed"] is False
    assert payload["current_commit"] == head
    assert payload["dirty"] is True
    assert payload["dirty_paths"]


def test_candidate_identity_audit_detects_head_change(
    tmp_path: Path,
) -> None:
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    subprocess.run(
        ("git", "config", "user.email", "ptl-test@example.invalid"),
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ("git", "config", "user.name", "PTL Test"),
        cwd=tmp_path,
        check=True,
    )
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("first\n", encoding="utf-8")
    subprocess.run(("git", "add", "tracked.txt"), cwd=tmp_path, check=True)
    subprocess.run(
        ("git", "commit", "-qm", "first"),
        cwd=tmp_path,
        check=True,
    )
    expected = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    tracked.write_text("second\n", encoding="utf-8")
    subprocess.run(("git", "add", "tracked.txt"), cwd=tmp_path, check=True)
    subprocess.run(
        ("git", "commit", "-qm", "second"),
        cwd=tmp_path,
        check=True,
    )

    payload = audit_candidate_identity(tmp_path, expected)

    assert payload["passed"] is False
    assert payload["current_commit"] != expected
    assert payload["dirty"] is False

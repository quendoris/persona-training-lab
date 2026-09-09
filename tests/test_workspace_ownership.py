from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from persona_training_lab.bootstrap.workspace_ownership import (
    WorkspaceAlreadyOpenError,
    WorkspaceOwnership,
)


def test_workspace_ownership_is_exclusive_and_releasable(tmp_path) -> None:
    first = WorkspaceOwnership(tmp_path)
    second = WorkspaceOwnership(tmp_path)

    first.acquire()
    first.acquire()
    assert first.acquired
    assert first.lock_path == tmp_path.resolve() / ".ptl-workspace.lock"

    with pytest.raises(WorkspaceAlreadyOpenError, match="already open for writing"):
        second.acquire()

    first.release()
    first.release()
    assert not first.acquired

    second.acquire()
    assert second.acquired
    second.release()


def test_workspace_ownership_blocks_a_second_process(tmp_path) -> None:
    owner = WorkspaceOwnership(tmp_path)
    owner.acquire()
    try:
        blocked = _probe_from_child_process(tmp_path)
        assert blocked.returncode == 7, blocked.stderr
    finally:
        owner.release()

    available = _probe_from_child_process(tmp_path)
    assert available.returncode == 0, available.stderr


def _probe_from_child_process(workspace: Path) -> subprocess.CompletedProcess[str]:
    script = """
from pathlib import Path
import sys
from persona_training_lab.bootstrap.workspace_ownership import (
    WorkspaceAlreadyOpenError,
    WorkspaceOwnership,
)

owner = WorkspaceOwnership(Path(sys.argv[1]))
try:
    owner.acquire()
except WorkspaceAlreadyOpenError:
    raise SystemExit(7)
owner.release()
"""
    return subprocess.run(
        [sys.executable, "-c", script, str(workspace)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

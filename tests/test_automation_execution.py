from __future__ import annotations

from pathlib import Path
import os
import sys

import psutil
import pytest

from persona_training_lab.application.automation.execution import (
    AutomationExecution,
    run_automation_process,
)


def _environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment["PYTHONUNBUFFERED"] = "1"
    return environment


def test_automation_execution_drains_large_output_without_unbounded_capture(
    tmp_path: Path,
) -> None:
    result = run_automation_process(
        AutomationExecution(
            mode="exec",
            argv=(
                sys.executable,
                "-c",
                (
                    "import sys; "
                    "sys.stdout.write('x' * 8192); "
                    "sys.stderr.write('y' * 8192)"
                ),
            ),
            cwd=tmp_path,
            env=_environment(),
            output_limit_bytes=256,
        ),
        cancel_requested=None,
    )

    assert result.return_code == 0
    assert result.stdout == "x" * 256
    assert result.stderr == "y" * 256
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True


def test_automation_execution_keeps_shell_mode_explicit(tmp_path: Path) -> None:
    result = run_automation_process(
        AutomationExecution(
            mode="shell",
            shell_command="echo ptl-shell-contract",
            cwd=tmp_path,
            env=_environment(),
        ),
        cancel_requested=None,
    )

    assert result.return_code == 0
    assert "ptl-shell-contract" in result.stdout
    assert result.cancelled is False
    assert result.timed_out is False


@pytest.mark.parametrize(
    "execution",
    (
        AutomationExecution,
    ),
)
def test_automation_execution_contract_rejects_ambiguous_command_shapes(
    tmp_path: Path,
    execution,
) -> None:
    with pytest.raises(ValueError, match="non-empty argv"):
        execution(mode="exec", cwd=tmp_path)
    with pytest.raises(ValueError, match="must not define shell_command"):
        execution(
            mode="exec",
            argv=("tool",),
            shell_command="echo hidden-shell",
            cwd=tmp_path,
        )
    with pytest.raises(ValueError, match="must not define argv"):
        execution(
            mode="shell",
            argv=("tool",),
            shell_command="echo explicit-shell",
            cwd=tmp_path,
        )


def test_automation_timeout_terminates_descendant_process_tree(tmp_path: Path) -> None:
    child_pid_path = tmp_path / "child.pid"
    script = (
        "import pathlib, subprocess, sys, time; "
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import time; time.sleep(30)']); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8'); "
        "time.sleep(30)"
    )
    result = run_automation_process(
        AutomationExecution(
            mode="exec",
            argv=(sys.executable, "-c", script, str(child_pid_path)),
            cwd=tmp_path,
            env=_environment(),
            timeout=1.0,
        ),
        cancel_requested=None,
    )

    assert result.timed_out is True
    assert result.cancelled is False
    assert child_pid_path.exists()
    child_pid = int(child_pid_path.read_text(encoding="utf-8"))
    try:
        child = psutil.Process(child_pid)
    except psutil.NoSuchProcess:
        return
    assert not child.is_running() or child.status() == psutil.STATUS_ZOMBIE

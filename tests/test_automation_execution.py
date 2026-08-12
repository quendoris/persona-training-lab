from __future__ import annotations

from pathlib import Path
import os
import sys
import time

import psutil
import pytest

from persona_training_lab.application.automation.execution import (
    MAX_AUTOMATION_OUTPUT_LIMIT_BYTES,
    AutomationExecution,
    run_automation_process,
)


def _environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment["PYTHONUNBUFFERED"] = "1"
    return environment


def _assert_process_gone(pid: int) -> None:
    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    assert not process.is_running() or process.status() == psutil.STATUS_ZOMBIE


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


def test_automation_execution_contract_rejects_ambiguous_command_shapes(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="non-empty argv"):
        AutomationExecution(mode="exec", cwd=tmp_path)
    with pytest.raises(ValueError, match="must not define shell_command"):
        AutomationExecution(
            mode="exec",
            argv=("tool",),
            shell_command="echo hidden-shell",
            cwd=tmp_path,
        )
    with pytest.raises(ValueError, match="must not define argv"):
        AutomationExecution(
            mode="shell",
            argv=("tool",),
            shell_command="echo explicit-shell",
            cwd=tmp_path,
        )
    with pytest.raises(ValueError, match="hard maximum"):
        AutomationExecution(
            mode="exec",
            argv=("tool",),
            cwd=tmp_path,
            output_limit_bytes=MAX_AUTOMATION_OUTPUT_LIMIT_BYTES + 1,
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
    _assert_process_gone(int(child_pid_path.read_text(encoding="utf-8")))


def test_automation_cancellation_terminates_descendant_process_tree(
    tmp_path: Path,
) -> None:
    child_pid_path = tmp_path / "cancel-child.pid"
    script = (
        "import pathlib, subprocess, sys, time; "
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import time; time.sleep(30)']); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8'); "
        "time.sleep(30)"
    )
    started = time.monotonic()
    result = run_automation_process(
        AutomationExecution(
            mode="exec",
            argv=(sys.executable, "-c", script, str(child_pid_path)),
            cwd=tmp_path,
            env=_environment(),
        ),
        cancel_requested=lambda: time.monotonic() - started >= 0.5,
    )

    assert result.cancelled is True
    assert result.timed_out is False
    assert child_pid_path.exists()
    _assert_process_gone(int(child_pid_path.read_text(encoding="utf-8")))


@pytest.mark.skipif(os.name == "nt", reason="POSIX session containment contract")
def test_automation_success_does_not_leave_background_descendants(
    tmp_path: Path,
) -> None:
    child_pid_path = tmp_path / "background-child.pid"
    script = (
        "import pathlib, subprocess, sys; "
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import time; time.sleep(30)']); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding='utf-8')"
    )
    result = run_automation_process(
        AutomationExecution(
            mode="exec",
            argv=(sys.executable, "-c", script, str(child_pid_path)),
            cwd=tmp_path,
            env=_environment(),
        ),
        cancel_requested=None,
    )

    assert result.return_code == 0
    assert child_pid_path.exists()
    _assert_process_gone(int(child_pid_path.read_text(encoding="utf-8")))

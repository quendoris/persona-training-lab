from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

from persona_training_lab.application.automation import _windows_job_runner


def _launcher_path() -> Path:
    return Path(_windows_job_runner.__file__).resolve()


def _payload(*, argv: list[str]) -> bytes:
    return json.dumps(
        {
            "mode": "exec",
            "argv": argv,
            "shell_command": "",
            "cwd": str(Path.cwd()),
            "env": {"PTL_WINDOWS_LAUNCHER_TEST": "1"},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def test_windows_automation_launcher_blocks_until_parent_releases_payload() -> None:
    process = subprocess.Popen(
        (sys.executable, str(_launcher_path())),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    try:
        time.sleep(0.1)
        assert process.poll() is None
        stdout, stderr = process.communicate(
            _payload(
                argv=(
                    [
                        sys.executable,
                        "-c",
                        "print('launcher-released')",
                    ]
                )
            ),
            timeout=5,
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    assert process.returncode == 0
    assert stdout.decode("utf-8").strip() == "launcher-released"
    assert stderr == b""


def test_windows_automation_launcher_preserves_exec_argument_boundaries() -> None:
    argument = "a b;$HOME|literal"
    completed = subprocess.run(
        (sys.executable, str(_launcher_path())),
        input=_payload(
            argv=[
                sys.executable,
                "-c",
                "import sys; print(repr(sys.argv[1]))",
                argument,
            ]
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 0
    assert completed.stdout.decode("utf-8").strip() == repr(argument)
    assert completed.stderr == b""


def test_windows_automation_launcher_rejects_invalid_payload_before_launch() -> None:
    completed = subprocess.run(
        (sys.executable, str(_launcher_path())),
        input=json.dumps(
            {
                "mode": "exec",
                "argv": [],
                "shell_command": "",
                "cwd": str(Path.cwd()),
                "env": {},
            }
        ).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 127
    assert completed.stdout == b""
    assert (
        completed.stderr.decode("utf-8").strip()
        == "ptl_automation_windows_launcher_failed:payload_exec_shape"
    )

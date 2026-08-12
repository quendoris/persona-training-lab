from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import TypedDict, cast


class _ExecutionPayload(TypedDict):
    mode: str
    argv: list[str]
    shell_command: str
    cwd: str
    env: dict[str, str]


def _read_payload() -> _ExecutionPayload:
    raw = sys.stdin.buffer.read()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("payload_object")
    mode = value.get("mode")
    argv = value.get("argv")
    shell_command = value.get("shell_command")
    cwd = value.get("cwd")
    env = value.get("env")
    if mode not in {"exec", "shell"}:
        raise ValueError("payload_mode")
    if not isinstance(argv, list) or not all(
        isinstance(item, str) for item in argv
    ):
        raise ValueError("payload_argv")
    if not isinstance(shell_command, str):
        raise ValueError("payload_shell_command")
    if not isinstance(cwd, str) or not cwd:
        raise ValueError("payload_working_directory")
    if not isinstance(env, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in env.items()
    ):
        raise ValueError("payload_environment")
    if mode == "exec" and (not argv or not argv[0].strip() or shell_command):
        raise ValueError("payload_exec_shape")
    if mode == "shell" and (not shell_command.strip() or argv):
        raise ValueError("payload_shell_shape")
    return cast(
        _ExecutionPayload,
        {
            "mode": mode,
            "argv": argv,
            "shell_command": shell_command,
            "cwd": cwd,
            "env": env,
        },
    )


def _run(payload: _ExecutionPayload) -> int:
    mode = payload["mode"]
    command: list[str] | str = (
        payload["shell_command"] if mode == "shell" else payload["argv"]
    )
    process = subprocess.Popen(
        command,
        cwd=Path(payload["cwd"]),
        env=payload["env"],
        stdin=subprocess.DEVNULL,
        stdout=None,
        stderr=None,
        shell=mode == "shell",
        close_fds=os.name != "nt",
    )
    return process.wait()


def main() -> int:
    try:
        payload = _read_payload()
        return _run(payload)
    except Exception as exc:
        code = str(exc).strip() or type(exc).__name__
        print(f"ptl_automation_windows_launcher_failed:{code}", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())

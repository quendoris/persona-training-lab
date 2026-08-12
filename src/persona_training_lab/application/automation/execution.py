from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import json
from pathlib import Path
import os
import signal
import subprocess
import sys
from threading import Thread
import time
from types import MappingProxyType
from typing import BinaryIO, Literal, Mapping, Protocol

from persona_training_lab.application.automation.windows_job import WindowsJobObject


AutomationExecutionMode = Literal["exec", "shell"]
DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES = 1024 * 1024
MAX_AUTOMATION_OUTPUT_LIMIT_BYTES = 64 * 1024 * 1024
_PROCESS_POLL_INTERVAL_SECONDS = 0.05
_PROCESS_TERMINATION_GRACE_SECONDS = 2.0
_CAPTURE_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class AutomationExecution:
    mode: AutomationExecutionMode
    cwd: Path
    env: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    argv: tuple[str, ...] = ()
    shell_command: str = ""
    timeout: float | None = None
    output_limit_bytes: int = DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES

    def __post_init__(self) -> None:
        if self.mode == "exec":
            if not self.argv or not self.argv[0].strip():
                raise ValueError("exec automation requires a non-empty argv")
            if self.shell_command:
                raise ValueError("exec automation must not define shell_command")
        elif self.mode == "shell":
            if not self.shell_command.strip():
                raise ValueError("shell automation requires a non-empty command")
            if self.argv:
                raise ValueError("shell automation must not define argv")
        else:
            raise ValueError(f"unsupported automation execution mode: {self.mode}")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("automation timeout must be positive")
        if self.output_limit_bytes < 0:
            raise ValueError("automation output limit must not be negative")
        if self.output_limit_bytes > MAX_AUTOMATION_OUTPUT_LIMIT_BYTES:
            raise ValueError("automation output limit exceeds the hard maximum")

    @property
    def command_snapshot(self) -> tuple[str, ...]:
        if self.mode == "exec":
            return self.argv
        return (self.shell_command,)


@dataclass(frozen=True, slots=True)
class AutomationProcessResult:
    return_code: int
    stdout: str = ""
    stderr: str = ""
    cancelled: bool = False
    timed_out: bool = False
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class AutomationProcessRunner(Protocol):
    def __call__(
        self,
        execution: AutomationExecution,
        *,
        cancel_requested: Callable[[], bool] | None,
    ) -> AutomationProcessResult: ...


@dataclass(slots=True)
class _BoundedCapture:
    limit: int
    data: bytearray = field(default_factory=bytearray)
    truncated: bool = False

    def append(self, chunk: bytes) -> None:
        remaining = max(0, self.limit - len(self.data))
        if remaining:
            self.data.extend(chunk[:remaining])
        if len(chunk) > remaining:
            self.truncated = True

    def text(self) -> str:
        return bytes(self.data).decode("utf-8", errors="replace")


@dataclass(slots=True)
class _ContainedProcess:
    process: subprocess.Popen[bytes]
    terminate_tree: Callable[[], None]
    finalize_tree: Callable[[], None]


def _drain_stream(stream: BinaryIO, capture: _BoundedCapture) -> None:
    try:
        while True:
            chunk = stream.read(_CAPTURE_CHUNK_BYTES)
            if not chunk:
                return
            capture.append(chunk)
    finally:
        stream.close()


def _posix_process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _terminate_posix_process_group(process_group_id: int) -> None:
    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        return

    deadline = time.monotonic() + _PROCESS_TERMINATION_GRACE_SECONDS
    while time.monotonic() < deadline:
        if not _posix_process_group_exists(process_group_id):
            return
        time.sleep(_PROCESS_POLL_INTERVAL_SECONDS)

    try:
        os.killpg(process_group_id, signal.SIGKILL)
    except ProcessLookupError:
        return


def _spawn_posix_process(execution: AutomationExecution) -> _ContainedProcess:
    command: tuple[str, ...] | str = (
        execution.shell_command if execution.mode == "shell" else execution.argv
    )
    process = subprocess.Popen(
        command,
        cwd=execution.cwd,
        env=dict(execution.env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        shell=execution.mode == "shell",
        text=False,
        start_new_session=True,
    )
    process_group_id = process.pid
    terminate = lambda: _terminate_posix_process_group(process_group_id)
    return _ContainedProcess(process, terminate, terminate)


def _windows_launch_payload(execution: AutomationExecution) -> bytes:
    return json.dumps(
        {
            "mode": execution.mode,
            "argv": list(execution.argv),
            "shell_command": execution.shell_command,
            "cwd": str(execution.cwd),
            "env": dict(execution.env),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _spawn_windows_process(execution: AutomationExecution) -> _ContainedProcess:
    job = WindowsJobObject.create_kill_on_close()
    helper = Path(__file__).with_name("_windows_job_runner.py")
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            (sys.executable, str(helper)),
            cwd=execution.cwd,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=False,
        )
        job.assign(process)
        if process.stdin is None:
            raise RuntimeError("automation Windows launcher pipe was not created")
        process.stdin.write(_windows_launch_payload(execution))
        process.stdin.close()
    except Exception:
        try:
            job.terminate()
        except OSError:
            if process is not None and process.poll() is None:
                process.kill()
        finally:
            job.close()
        raise

    def terminate() -> None:
        try:
            job.terminate()
        except OSError:
            if process.poll() is None:
                process.kill()

    return _ContainedProcess(process, terminate, job.close)


def _spawn_contained_process(execution: AutomationExecution) -> _ContainedProcess:
    if os.name == "nt":
        return _spawn_windows_process(execution)
    return _spawn_posix_process(execution)


def run_automation_process(
    execution: AutomationExecution,
    *,
    cancel_requested: Callable[[], bool] | None,
) -> AutomationProcessResult:
    contained = _spawn_contained_process(execution)
    process = contained.process
    if process.stdout is None or process.stderr is None:
        contained.terminate_tree()
        contained.finalize_tree()
        raise RuntimeError("automation process pipes were not created")

    stdout_capture = _BoundedCapture(execution.output_limit_bytes)
    stderr_capture = _BoundedCapture(execution.output_limit_bytes)
    stdout_thread = Thread(
        target=_drain_stream,
        args=(process.stdout, stdout_capture),
        daemon=True,
    )
    stderr_thread = Thread(
        target=_drain_stream,
        args=(process.stderr, stderr_capture),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    started = time.monotonic()
    cancelled = False
    timed_out = False
    try:
        while process.poll() is None:
            if cancel_requested is not None and cancel_requested():
                cancelled = True
                contained.terminate_tree()
                break
            if (
                execution.timeout is not None
                and time.monotonic() - started >= execution.timeout
            ):
                timed_out = True
                contained.terminate_tree()
                break
            time.sleep(_PROCESS_POLL_INTERVAL_SECONDS)

        return_code = process.wait()
    finally:
        contained.finalize_tree()

    stdout_thread.join(timeout=_PROCESS_TERMINATION_GRACE_SECONDS)
    stderr_thread.join(timeout=_PROCESS_TERMINATION_GRACE_SECONDS)
    return AutomationProcessResult(
        return_code=return_code,
        stdout=stdout_capture.text(),
        stderr=stderr_capture.text(),
        cancelled=cancelled,
        timed_out=timed_out,
        stdout_truncated=stdout_capture.truncated,
        stderr_truncated=stderr_capture.truncated,
    )

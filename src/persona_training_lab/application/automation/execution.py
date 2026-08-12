from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import os
import subprocess
from threading import Thread
import time
from types import MappingProxyType
from typing import Literal, Mapping, Protocol

import psutil


AutomationExecutionMode = Literal["exec", "shell"]
DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES = 1024 * 1024
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


def _drain_stream(stream: object, capture: _BoundedCapture) -> None:
    read = getattr(stream, "read")
    try:
        while True:
            chunk = read(_CAPTURE_CHUNK_BYTES)
            if not chunk:
                return
            capture.append(bytes(chunk))
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        root = psutil.Process(process.pid)
        processes = (*root.children(recursive=True), root)
        for item in processes:
            try:
                item.terminate()
            except psutil.NoSuchProcess:
                continue
        _gone, alive = psutil.wait_procs(
            processes,
            timeout=_PROCESS_TERMINATION_GRACE_SECONDS,
        )
        for item in alive:
            try:
                item.kill()
            except psutil.NoSuchProcess:
                continue
        if alive:
            psutil.wait_procs(
                alive,
                timeout=_PROCESS_TERMINATION_GRACE_SECONDS,
            )
    except psutil.Error:
        try:
            process.terminate()
            process.wait(timeout=_PROCESS_TERMINATION_GRACE_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()


def run_automation_process(
    execution: AutomationExecution,
    *,
    cancel_requested: Callable[[], bool] | None,
) -> AutomationProcessResult:
    popen_command: tuple[str, ...] | str
    shell = execution.mode == "shell"
    if shell:
        popen_command = execution.shell_command
    else:
        popen_command = execution.argv

    popen_kwargs: dict[str, object] = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    process = subprocess.Popen(
        popen_command,
        cwd=execution.cwd,
        env=dict(execution.env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        shell=shell,
        text=False,
        **popen_kwargs,
    )
    if process.stdout is None or process.stderr is None:
        _terminate_process_tree(process)
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
    while process.poll() is None:
        if cancel_requested is not None and cancel_requested():
            cancelled = True
            _terminate_process_tree(process)
            break
        if execution.timeout is not None and time.monotonic() - started >= execution.timeout:
            timed_out = True
            _terminate_process_tree(process)
            break
        time.sleep(_PROCESS_POLL_INTERVAL_SECONDS)

    return_code = process.wait()
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

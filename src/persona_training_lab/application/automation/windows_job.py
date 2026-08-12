from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
import subprocess
from typing import Any, Callable, cast


_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100


class _IOCounters(ctypes.Structure):
    _fields_ = (
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    )


class _JobObjectBasicLimitInformation(ctypes.Structure):
    _fields_ = (
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    )


class _JobObjectExtendedLimitInformation(ctypes.Structure):
    _fields_ = (
        ("BasicLimitInformation", _JobObjectBasicLimitInformation),
        ("IoInfo", _IOCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    )


def _kernel32() -> Any:
    if os.name != "nt":
        raise OSError("Windows Job Objects are only available on Windows")
    loader = getattr(ctypes, "WinDLL", None)
    if loader is None:
        raise OSError("Windows API loader is unavailable")
    return loader("kernel32", use_last_error=True)


def _last_windows_error() -> int:
    reader = cast(Callable[[], int] | None, getattr(ctypes, "get_last_error", None))
    return int(reader()) if reader is not None else 0


def _raise_windows_error(function: str) -> None:
    code = _last_windows_error()
    raise OSError(code, f"{function} failed with Windows error {code}")


@dataclass(slots=True)
class WindowsJobObject:
    _handle: int
    _closed: bool = False

    @classmethod
    def create_kill_on_close(cls) -> WindowsJobObject:
        kernel32 = _kernel32()
        create_job = kernel32.CreateJobObjectW
        create_job.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        create_job.restype = wintypes.HANDLE
        handle = create_job(None, None)
        if not handle:
            _raise_windows_error("CreateJobObjectW")

        information = _JobObjectExtendedLimitInformation()
        information.BasicLimitInformation.LimitFlags = (
            _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        set_information = kernel32.SetInformationJobObject
        set_information.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        set_information.restype = wintypes.BOOL
        if not set_information(
            handle,
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(information),
            ctypes.sizeof(information),
        ):
            kernel32.CloseHandle(handle)
            _raise_windows_error("SetInformationJobObject")
        return cls(int(handle))

    def assign(self, process: subprocess.Popen[bytes]) -> None:
        if self._closed:
            raise RuntimeError("Windows Job Object is already closed")
        kernel32 = _kernel32()
        open_process = kernel32.OpenProcess
        open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        open_process.restype = wintypes.HANDLE
        process_handle = open_process(
            _PROCESS_TERMINATE | _PROCESS_SET_QUOTA,
            False,
            process.pid,
        )
        if not process_handle:
            _raise_windows_error("OpenProcess")
        try:
            assign_process = kernel32.AssignProcessToJobObject
            assign_process.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
            assign_process.restype = wintypes.BOOL
            if not assign_process(self._handle, process_handle):
                _raise_windows_error("AssignProcessToJobObject")
        finally:
            kernel32.CloseHandle(process_handle)

    def terminate(self, exit_code: int = 1) -> None:
        if self._closed:
            return
        kernel32 = _kernel32()
        terminate_job = kernel32.TerminateJobObject
        terminate_job.argtypes = (wintypes.HANDLE, wintypes.UINT)
        terminate_job.restype = wintypes.BOOL
        if not terminate_job(self._handle, exit_code):
            _raise_windows_error("TerminateJobObject")

    def close(self) -> None:
        if self._closed:
            return
        kernel32 = _kernel32()
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL
        handle = self._handle
        self._closed = True
        self._handle = 0
        if not close_handle(handle):
            _raise_windows_error("CloseHandle")

    def __enter__(self) -> WindowsJobObject:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

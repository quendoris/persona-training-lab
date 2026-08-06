from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.ui.shell.main_window_background import MainWindow


class _CloseEvent:
    def __init__(self) -> None:
        self.ignored = 0

    def ignore(self) -> None:
        self.ignored += 1


def test_close_retry_does_not_repeat_leave_guard_or_block_gui_thread() -> None:
    leave_calls: list[str] = []
    shutdown_timeouts: list[int] = []
    retry_calls: list[str] = []
    status_calls: list[str] = []
    window = SimpleNamespace(
        _close_guard_passed=False,
        _workspace=SimpleNamespace(
            request_current_leave=lambda: leave_calls.append("leave") or True,
        ),
        shutdown_background_work=lambda timeout: (
            shutdown_timeouts.append(timeout) or False
        ),
        _set_background_shutdown_status=lambda: status_calls.append("status"),
        _schedule_close_retry=lambda: retry_calls.append("retry"),
    )
    event = _CloseEvent()

    MainWindow.closeEvent(window, event)  # type: ignore[arg-type]
    MainWindow.closeEvent(window, event)  # type: ignore[arg-type]

    assert leave_calls == ["leave"]
    assert shutdown_timeouts == [0, 0]
    assert status_calls == ["status", "status"]
    assert retry_calls == ["retry", "retry"]
    assert event.ignored == 2

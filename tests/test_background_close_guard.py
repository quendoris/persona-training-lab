from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.ui.automation.screen import AutomationScreen
from persona_training_lab.ui.shell.main_window_background import MainWindow
from persona_training_lab.ui.training.screen import TrainingScreen


class _CloseEvent:
    def __init__(self) -> None:
        self.ignored = 0

    def ignore(self) -> None:
        self.ignored += 1


class _FakeThread:
    def __init__(self, *, running: bool = True, finish_on_wait: bool = False) -> None:
        self.running = running
        self.finish_on_wait = finish_on_wait
        self.quit_calls = 0
        self.wait_calls: list[int] = []

    def isRunning(self) -> bool:  # noqa: N802
        return self.running

    def quit(self) -> None:
        self.quit_calls += 1

    def wait(self, timeout_ms: int) -> bool:
        self.wait_calls.append(timeout_ms)
        if self.finish_on_wait:
            self.running = False
        return not self.running


class _FakeWorker:
    def __init__(self) -> None:
        self.cancel_calls = 0

    def cancel(self) -> None:
        self.cancel_calls += 1


def test_close_retry_does_not_repeat_leave_guard_or_block_gui_thread() -> None:
    leave_calls: list[str] = []
    shutdown_timeouts: list[int] = []
    retry_calls: list[str] = []
    status_calls: list[str] = []
    window = SimpleNamespace(
        _close_guard_passed=False,
        _workspace=SimpleNamespace(
            request_current_close=lambda: leave_calls.append("leave") or True,
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


def test_main_window_shutdown_visits_every_background_owner() -> None:
    calls: list[tuple[str, int]] = []
    first = SimpleNamespace(
        shutdown_background_work=lambda timeout: (
            calls.append(("first", timeout)) or False
        )
    )
    passive = SimpleNamespace()
    second = SimpleNamespace(
        shutdown_background_work=lambda timeout: (
            calls.append(("second", timeout)) or True
        )
    )
    window = SimpleNamespace(
        _workspace=SimpleNamespace(workspaces=lambda: (first, passive, second))
    )

    assert MainWindow.shutdown_background_work(window, 0) is False  # type: ignore[arg-type]
    assert calls == [("first", 0), ("second", 0)]


def test_training_shutdown_waits_without_destroying_running_worker() -> None:
    thread = _FakeThread(running=True, finish_on_wait=False)
    timer = SimpleNamespace(stop_calls=0)
    timer.stop = lambda: setattr(timer, "stop_calls", timer.stop_calls + 1)
    screen = SimpleNamespace(
        _runner_timer=timer,
        _logs_dialog=None,
        _inference_thread=thread,
        _training_thread=None,
        _thread_is_running=TrainingScreen._thread_is_running,
    )

    assert TrainingScreen.shutdown_background_work(screen, 0) is False  # type: ignore[arg-type]
    assert thread.quit_calls == 1
    assert thread.wait_calls == []
    assert timer.stop_calls == 1

    thread.finish_on_wait = True
    assert TrainingScreen.shutdown_background_work(screen, 50) is True  # type: ignore[arg-type]
    assert thread.wait_calls and 0 < thread.wait_calls[-1] <= 50


def test_automation_shutdown_requests_cooperative_cancel_before_wait() -> None:
    thread = _FakeThread(running=True, finish_on_wait=True)
    worker = _FakeWorker()
    screen = SimpleNamespace(
        _worker=worker,
        _thread=thread,
        _thread_is_running=AutomationScreen._thread_is_running,
    )

    assert AutomationScreen.shutdown_background_work(screen, 50) is True  # type: ignore[arg-type]
    assert worker.cancel_calls == 1
    assert thread.quit_calls == 1
    assert thread.wait_calls == [50]

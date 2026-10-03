from __future__ import annotations

from types import SimpleNamespace

import pytest

from persona_training_lab.bootstrap.app import _drain_background_work
from persona_training_lab.ui.automation.screen import AutomationScreen
from persona_training_lab.ui.panels.telemetry_panel import TelemetryPanel
from persona_training_lab.ui.shell.main_window_background import MainWindow
from persona_training_lab.ui.tests.screen import TestsScreen as _TestsScreen
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




class _FakePythonThread:
    def __init__(self, *, alive: bool = True, finish_on_join: bool = False) -> None:
        self.alive = alive
        self.finish_on_join = finish_on_join
        self.join_calls: list[float] = []

    def is_alive(self) -> bool:
        return self.alive

    def join(self, timeout: float) -> None:
        self.join_calls.append(timeout)
        if self.finish_on_join:
            self.alive = False


class _FakeDock:
    def __init__(self, panel: object) -> None:
        self._panel = panel

    def widget(self) -> object:
        return self._panel

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


def test_shutdown_drain_does_not_release_after_one_failed_attempt() -> None:
    calls: list[int] = []
    results = iter((False, False, True))
    window = SimpleNamespace(
        shutdown_background_work=lambda timeout: (
            calls.append(timeout) or next(results)
        )
    )

    _drain_background_work(
        window,  # type: ignore[arg-type]
        slice_ms=17,
        retry_sleep_seconds=0,
    )

    assert calls == [17, 17, 17]


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


def test_evaluation_shutdown_participates_in_shell_close_guard() -> None:
    thread = _FakeThread(running=True, finish_on_wait=False)
    dialog = SimpleNamespace(close_calls=0)
    dialog.close = lambda: setattr(dialog, "close_calls", dialog.close_calls + 1)
    screen = SimpleNamespace(
        _cases_dialog=dialog,
        _tests_thread=thread,
        _thread_is_running=_TestsScreen._thread_is_running,
    )

    assert _TestsScreen.shutdown_background_work(screen, 0) is False  # type: ignore[arg-type]
    assert thread.quit_calls == 1
    assert thread.wait_calls == []
    assert dialog.close_calls == 1

    thread.finish_on_wait = True
    assert _TestsScreen.shutdown_background_work(screen, 50) is True  # type: ignore[arg-type]
    assert thread.wait_calls == [50]


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


def test_main_window_shutdown_includes_dock_background_owner() -> None:
    calls: list[tuple[str, int]] = []
    workspace = SimpleNamespace(
        shutdown_background_work=lambda timeout: (
            calls.append(("workspace", timeout)) or True
        )
    )
    telemetry = SimpleNamespace(
        shutdown_background_work=lambda timeout: (
            calls.append(("telemetry", timeout)) or False
        )
    )
    window = SimpleNamespace(
        _workspace=SimpleNamespace(workspaces=lambda: (workspace,)),
        _docks={"telemetry": _FakeDock(telemetry)},
    )

    assert MainWindow.shutdown_background_work(window, 0) is False  # type: ignore[arg-type]
    assert calls == [("workspace", 0), ("telemetry", 0)]


def test_telemetry_shutdown_waits_for_inflight_collection() -> None:
    thread = _FakePythonThread(alive=True, finish_on_join=False)
    timer = SimpleNamespace(stop_calls=0)
    timer.stop = lambda: setattr(timer, "stop_calls", timer.stop_calls + 1)
    panel = SimpleNamespace(
        _auto_refresh_timer=timer,
        _refresh_thread=thread,
    )

    assert TelemetryPanel.shutdown_background_work(panel, 0) is False  # type: ignore[arg-type]
    assert thread.join_calls == []
    assert timer.stop_calls == 1

    thread.finish_on_join = True
    assert TelemetryPanel.shutdown_background_work(panel, 50) is True  # type: ignore[arg-type]
    assert thread.join_calls == [0.05]
    assert timer.stop_calls == 2


def test_telemetry_refresh_starts_worker_without_collecting_inline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collected: list[str] = []
    started: list[str] = []

    class _DeferredThread:
        def __init__(self, *, target, name: str, daemon: bool) -> None:
            assert name == "ptl-telemetry-refresh"
            assert daemon is False
            self.target = target

        def start(self) -> None:
            started.append("start")

    monkeypatch.setattr(
        "persona_training_lab.ui.panels.telemetry_panel.Thread",
        _DeferredThread,
    )
    button = SimpleNamespace()
    button.setEnabled = lambda _enabled: None
    button.setText = lambda _text: None
    panel = SimpleNamespace(
        _refresh_pending=False,
        _refresh_thread=None,
        _refresh_btn=button,
        _text=lambda key: key,
        _collect_refresh_snapshot=lambda: collected.append("collect"),
    )

    TelemetryPanel._run_refresh(  # type: ignore[arg-type]
        panel,
        show_pending=True,
    )

    assert started == ["start"]
    assert collected == []
    assert panel._refresh_pending is True
    assert panel._refresh_thread is not None

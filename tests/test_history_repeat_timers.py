from __future__ import annotations

from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.agents.history_repeat_timers import HistoryRepeatTimers


_APP = QApplication.instance() or QApplication([])


def _timers(*, allowed: list[bool], calls: list[str]) -> HistoryRepeatTimers:
    return HistoryRepeatTimers(
        repeat_allowed=lambda: allowed[0],
        on_repeat=lambda: calls.append("undo"),
        delay_ms=330,
        interval_ms=85,
    )


def test_repeat_timer_configuration_is_owned_by_component() -> None:
    timers = _timers(allowed=[True], calls=[])

    assert timers.delay_timer.isSingleShot() is True
    assert timers.delay_timer.interval() == 330
    assert timers.repeat_timer.interval() == 85


def test_arm_starts_only_a_fresh_delay() -> None:
    timers = _timers(allowed=[True], calls=[])

    assert timers.arm() is True

    assert timers.delay_active is True
    assert timers.repeat_active is False


def test_rearm_after_ownership_loss_cancels_stale_delay() -> None:
    allowed = [True]
    timers = _timers(allowed=allowed, calls=[])
    assert timers.arm() is True
    assert timers.delay_active is True

    allowed[0] = False

    assert timers.arm() is False
    assert timers.delay_active is False
    assert timers.repeat_active is False


def test_delay_expiry_rechecks_repeat_permission() -> None:
    allowed = [True]
    timers = _timers(allowed=allowed, calls=[])
    assert timers.arm() is True

    allowed[0] = False

    assert timers.start_repeat() is False
    assert timers.delay_active is False
    assert timers.repeat_active is False


def test_repeat_tick_dispatches_only_while_permission_is_live() -> None:
    allowed = [True]
    calls: list[str] = []
    timers = _timers(allowed=allowed, calls=calls)
    assert timers.start_repeat() is True

    assert timers.tick() is True
    assert calls == ["undo"]
    assert timers.repeat_active is True

    allowed[0] = False

    assert timers.tick() is False
    assert calls == ["undo"]
    assert timers.delay_active is False
    assert timers.repeat_active is False


def test_stop_is_idempotent_and_stops_both_timer_phases() -> None:
    timers = _timers(allowed=[True], calls=[])
    assert timers.arm() is True

    timers.stop()
    timers.stop()

    assert timers.delay_active is False
    assert timers.repeat_active is False

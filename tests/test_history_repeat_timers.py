from __future__ import annotations

from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.agents.history_repeat_timers import HistoryRepeatTimers


_APP = QApplication.instance() or QApplication([])


def _timers() -> HistoryRepeatTimers:
    return HistoryRepeatTimers(delay_ms=330, interval_ms=85)


def test_repeat_timer_configuration_is_owned_by_component() -> None:
    timers = _timers()

    assert timers.delay_timer.isSingleShot() is True
    assert timers.delay_timer.interval() == 330
    assert timers.repeat_timer.interval() == 85


def test_arm_starts_only_a_fresh_delay() -> None:
    timers = _timers()

    timers.arm()

    assert timers.delay_active is True
    assert timers.repeat_active is False


def test_rearm_cancels_existing_repeat_phase() -> None:
    timers = _timers()
    timers.start_repeat()
    assert timers.repeat_active is True

    timers.arm()

    assert timers.delay_active is True
    assert timers.repeat_active is False


def test_start_repeat_promotes_delay_to_repeat_phase() -> None:
    timers = _timers()
    timers.arm()

    timers.start_repeat()

    assert timers.delay_active is False
    assert timers.repeat_active is True


def test_repeat_tick_emits_only_while_repeat_timer_is_active() -> None:
    calls: list[str] = []
    timers = _timers()
    timers.repeat_elapsed.connect(lambda: calls.append("repeat"))

    assert timers.tick() is False
    assert calls == []

    timers.start_repeat()

    assert timers.tick() is True
    assert calls == ["repeat"]


def test_stop_is_idempotent_and_stops_both_timer_phases() -> None:
    timers = _timers()
    timers.arm()

    timers.stop()
    timers.stop()

    assert timers.delay_active is False
    assert timers.repeat_active is False

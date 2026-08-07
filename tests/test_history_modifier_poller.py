from __future__ import annotations

from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.agents.history_modifier_poller import (
    HistoryModifierPoller,
)


_APP = QApplication.instance() or QApplication([])


def test_modifier_poller_owns_interval_and_starts_inactive() -> None:
    poller = HistoryModifierPoller(lambda: None, interval_ms=16)

    assert poller.timer.interval() == 16
    assert poller.active is False


def test_activating_poller_starts_timer_and_deactivation_stops_it() -> None:
    poller = HistoryModifierPoller(lambda: None)

    poller.set_active(True)
    assert poller.active is True

    poller.set_active(False)
    assert poller.active is False


def test_poll_once_is_silent_while_inactive() -> None:
    calls: list[str] = []
    poller = HistoryModifierPoller(lambda: calls.append("poll"))

    assert poller.poll_once() is False
    assert calls == []


def test_poll_once_dispatches_exactly_once_while_active() -> None:
    calls: list[str] = []
    poller = HistoryModifierPoller(lambda: calls.append("poll"))
    poller.set_active(True)

    assert poller.poll_once() is True
    assert calls == ["poll"]


def test_repeated_activation_does_not_create_parallel_timer_state() -> None:
    poller = HistoryModifierPoller(lambda: None)

    poller.set_active(True)
    timer_id = poller.timer.timerId()
    poller.set_active(True)

    assert poller.active is True
    assert poller.timer.timerId() == timer_id


def test_stop_is_idempotent_and_disables_manual_polling() -> None:
    calls: list[str] = []
    poller = HistoryModifierPoller(lambda: calls.append("poll"))
    poller.set_active(True)

    poller.stop()
    poller.stop()

    assert poller.active is False
    assert poller.poll_once() is False
    assert calls == []

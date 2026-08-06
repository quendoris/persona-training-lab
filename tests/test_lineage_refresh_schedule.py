from __future__ import annotations

from persona_training_lab.application.lineage.refresh_state import (
    LineageRefreshSchedule,
)


def test_requests_are_coalesced_into_one_follow_up_generation() -> None:
    schedule = LineageRefreshSchedule()

    first = schedule.request()
    assert first == 1
    assert schedule.request() is None
    assert schedule.request() is None
    assert schedule.pending is True

    decision = schedule.complete_success(first)

    assert decision.accepted is True
    assert decision.dispatch_generation == 2
    assert schedule.busy is True
    assert schedule.active_generation == 2
    assert schedule.pending is False


def test_stale_completion_cannot_release_the_active_generation() -> None:
    schedule = LineageRefreshSchedule()
    active = schedule.request()
    assert active == 1

    decision = schedule.complete_success(999)

    assert decision.accepted is False
    assert schedule.busy is True
    assert schedule.active_generation == active


def test_periodic_pending_request_is_dropped_after_failure_for_backoff() -> None:
    schedule = LineageRefreshSchedule(
        base_interval_ms=100,
        max_interval_ms=400,
    )
    first = schedule.request()
    assert first == 1
    assert schedule.request() is None

    decision = schedule.complete_failure(first)

    assert decision.accepted is True
    assert decision.dispatch_generation is None
    assert decision.interval_ms == 200
    assert schedule.busy is False
    assert schedule.pending is False


def test_forced_pending_request_retries_immediately_after_failure() -> None:
    schedule = LineageRefreshSchedule(
        base_interval_ms=100,
        max_interval_ms=400,
    )
    first = schedule.request()
    assert first == 1
    assert schedule.request(force=True) is None

    decision = schedule.complete_failure(first)

    assert decision.accepted is True
    assert decision.interval_ms == 200
    assert decision.dispatch_generation == 2
    assert schedule.busy is True
    assert schedule.active_generation == 2


def test_backoff_is_bounded_success_resets_it_and_stop_rejects_results() -> None:
    schedule = LineageRefreshSchedule(
        base_interval_ms=100,
        max_interval_ms=400,
    )

    first = schedule.request()
    schedule.complete_failure(first)
    second = schedule.request()
    schedule.complete_failure(second)
    third = schedule.request()
    failure = schedule.complete_failure(third)

    assert failure.interval_ms == 400

    fourth = schedule.request()
    success = schedule.complete_success(fourth)
    assert success.interval_ms == 100
    assert schedule.consecutive_failures == 0

    fifth = schedule.request()
    schedule.stop()
    late = schedule.complete_success(fifth)

    assert late.accepted is False
    assert schedule.request(force=True) is None

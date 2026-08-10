from __future__ import annotations

import json
import logging

from persona_training_lab.application.errors.reporter import (
    ApplicationErrorReporter,
)
from persona_training_lab.application.messages import UserMessage


class _MemoryEventLog:
    def __init__(self) -> None:
        self.records = []

    def append(self, record) -> None:
        self.records.append(record)


class _BrokenEventLog:
    def append(self, _record) -> None:
        raise OSError("storage unavailable")


def test_capture_returns_safe_user_reference_and_structured_event() -> None:
    events = _MemoryEventLog()
    reporter = ApplicationErrorReporter(events)
    message = UserMessage("error.python.worker_thread")

    try:
        raise RuntimeError("backend exploded")
    except RuntimeError as error:
        result = reporter.capture(
            error,
            component="training.worker",
            user_message=message,
            entity_kind="training_run",
            entity_id="trn_001",
            context={"token": "secret", "epoch": 2},
        )

    assert result.error_id.startswith("err_")
    assert result.correlation_id.startswith("corr_")
    assert result.user_message == message
    assert len(events.records) == 1
    payload = json.loads(events.records[0].payload_json)
    assert payload["exception_type"] == "RuntimeError"
    assert payload["context"]["token"] == "<redacted>"
    assert payload["context"]["epoch"] == 2


def test_duplicate_error_does_not_flood_event_storage() -> None:
    events = _MemoryEventLog()
    reporter = ApplicationErrorReporter(
        events,
        duplicate_window_seconds=60,
    )
    error = RuntimeError("same failure")
    message = UserMessage("error.python.main_thread")

    reporter.capture(
        error,
        component="ui.refresh",
        user_message=message,
    )
    reporter.capture(
        error,
        component="ui.refresh",
        user_message=message,
    )

    assert len(events.records) == 1


def test_reporting_failure_never_escapes_to_application(caplog) -> None:
    reporter = ApplicationErrorReporter(
        _BrokenEventLog(),
        logger=logging.getLogger("test.error_reporter"),
    )
    message = UserMessage("error.ui.event_dispatch")

    with caplog.at_level(logging.DEBUG):
        result = reporter.capture(
            ValueError("bad input"),
            component="ui.action",
            user_message=message,
        )

    assert result.user_message == message

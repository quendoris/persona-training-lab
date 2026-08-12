from __future__ import annotations

import json

from persona_training_lab.application.operations_center import OperationsCenterService
from persona_training_lab.application.ports.event_log import EventRecord
from persona_training_lab.application.runtime.operations import RuntimeOperation


class _EventLog:
    def __init__(self, records=()) -> None:
        self.records = list(records)

    def list_recent(self, limit: int = 50):
        return self.records[:limit]


class _Operations:
    def __init__(self, active=(), recent=()) -> None:
        self.active = list(active)
        self.recent = list(recent)

    def list_active_operations(self):
        return self.active

    def list_recent_operations(self, limit: int = 50):
        return self.recent[:limit]


def _operation(
    operation_id: str,
    kind: str,
    state: str,
    at: str,
) -> RuntimeOperation:
    return RuntimeOperation(
        operation_id=operation_id,
        operation_kind=kind,
        subject_kind="model_version",
        subject_id="mdl_001",
        state=state,
        correlation_id=f"corr_{operation_id}",
        owner_pid=1,
        started_at=at,
        heartbeat_at=at,
        finished_at=at if state not in {"running", "starting"} else "",
        error_message="boom" if state == "failed" else "",
    )


def _event(
    event_id: str,
    event_type: str,
    level: str,
    at: str,
) -> EventRecord:
    return EventRecord(
        id=event_id,
        event_type=event_type,
        entity_kind="training_run",
        entity_id="trn_001",
        correlation_id=f"corr_{event_id}",
        causation_id=None,
        payload_json=json.dumps(
            {
                "component": "training.backend",
                "level": level,
                "message": "diagnostic",
                "correlation_id": f"corr_{event_id}",
            }
        ),
        occurred_at=at,
    )


def test_active_training_is_mapped_to_training_workspace() -> None:
    service = OperationsCenterService(
        event_log=_EventLog(),
        runtime_operations=_Operations(
            active=(
                _operation(
                    "op_1",
                    "training",
                    "running",
                    "2026-08-04T10:00:00+00:00",
                ),
            )
        ),
    )

    item = service.active_items()[0]

    assert item.title == "training · mdl_001"
    assert item.summary == "mdl_001 · running"
    assert item.status == "running"
    assert item.severity == "active"
    assert item.target_screen == "training"
    assert item.focus_text == ""
    assert item.focus_key == "focus.training.start"
    assert item.operation_kind == "training"
    assert item.operation_state == "running"
    assert item.operation_subject == "mdl_001"

    automation = OperationsCenterService(
        event_log=_EventLog(),
        runtime_operations=_Operations(
            active=(
                _operation(
                    "op_automation",
                    "automation_recipe",
                    "running",
                    "2026-08-04T10:01:00+00:00",
                ),
                _operation(
                    "op_command",
                    "automation_command",
                    "running",
                    "2026-08-04T10:02:00+00:00",
                ),
            )
        ),
    ).active_items()
    assert [item.target_screen for item in automation] == [
        "automation",
        "automation",
    ]
    assert all(item.focus_key == "" for item in automation)
    assert [item.operation_kind for item in automation] == [
        "automation_recipe",
        "automation_command",
    ]


def test_warning_and_error_events_appear_in_problems() -> None:
    service = OperationsCenterService(
        event_log=_EventLog(
            (
                _event(
                    "evt_warning",
                    "application.notice",
                    "WARNING",
                    "2026-08-04T11:00:00+00:00",
                ),
                _event(
                    "evt_info",
                    "application.notice",
                    "INFO",
                    "2026-08-04T10:00:00+00:00",
                ),
                _event(
                    "evt_error",
                    "application.error",
                    "ERROR",
                    "2026-08-04T09:00:00+00:00",
                ),
            )
        ),
        runtime_operations=_Operations(),
    )

    issues = service.issue_items()

    assert [item.severity for item in issues] == ["warning", "error"]
    assert [item.status for item in issues] == ["warning", "error"]
    assert all(item.target_screen == "training" for item in issues)
    assert issues[0].title == "WARNING · training.backend"
    assert issues[0].summary == "diagnostic · corr_evt_warning"
    assert issues[1].title == "application.error · training.backend"
    assert all(item.focus_text == "" for item in issues)


def test_recent_activity_is_sorted_and_deduplicated() -> None:
    operation = _operation(
        "op_1",
        "personality_test",
        "succeeded",
        "2026-08-04T12:00:00+00:00",
    )
    service = OperationsCenterService(
        event_log=_EventLog(
            (
                _event(
                    "evt_1",
                    "application.notice",
                    "INFO",
                    "2026-08-04T13:00:00+00:00",
                ),
            )
        ),
        runtime_operations=_Operations(recent=(operation, operation)),
    )

    items = service.recent_activity()

    assert items[0].item_id == "event:evt_1"
    assert sum(item.item_id == "operation:op_1" for item in items) == 1
    portrait = next(item for item in items if item.item_id == "operation:op_1")
    assert portrait.target_screen == "tests"
    assert portrait.focus_key == "focus.tests.build_portrait"
    assert portrait.title == "personality_test · mdl_001"
    assert portrait.status == "succeeded"


def test_automation_audit_events_stay_persistent_without_duplicate_activity_items() -> None:
    audit_event = EventRecord(
        id="evt_automation_audit",
        event_type="automation.run.finished",
        entity_kind="automation_command",
        entity_id="command_1",
        correlation_id="corr_command_1",
        causation_id="op_command_1",
        payload_json=json.dumps(
            {
                "schema": "ptl:automation-audit:v1",
                "operation_id": "op_command_1",
                "state": "succeeded",
            }
        ),
        occurred_at="2026-08-04T14:00:00+00:00",
    )
    operation = _operation(
        "op_command_1",
        "automation_command",
        "succeeded",
        "2026-08-04T14:00:00+00:00",
    )
    service = OperationsCenterService(
        event_log=_EventLog((audit_event,)),
        runtime_operations=_Operations(recent=(operation,)),
    )

    items = service.recent_activity()

    assert len(items) == 1
    assert items[0].item_id == "operation:op_command_1"
    assert items[0].target_screen == "automation"

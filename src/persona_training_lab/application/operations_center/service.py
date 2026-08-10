from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol

from persona_training_lab.application.ports.event_log import EventRecord
from persona_training_lab.application.runtime.operations import RuntimeOperation


class EventLogReadPort(Protocol):
    def list_recent(self, limit: int = 50) -> list[EventRecord]: ...


class RuntimeOperationsReadPort(Protocol):
    def list_active_operations(self) -> list[RuntimeOperation]: ...

    def list_recent_operations(self, limit: int = 50) -> list[RuntimeOperation]: ...


@dataclass(slots=True, frozen=True)
class OperationsCenterItem:
    item_id: str
    title: str
    summary: str
    status: str
    severity: str
    occurred_at: str
    target_screen: str
    focus_text: str = ""
    correlation_id: str = ""
    operation_kind: str = ""
    operation_state: str = ""
    operation_subject: str = ""
    operation_error: str = ""
    focus_key: str = ""


@dataclass(slots=True)
class OperationsCenterService:
    event_log: EventLogReadPort
    runtime_operations: RuntimeOperationsReadPort

    def active_items(self) -> tuple[OperationsCenterItem, ...]:
        try:
            operations = self.runtime_operations.list_active_operations()
        except Exception:
            return ()
        return tuple(self._operation_item(operation) for operation in operations)

    def recent_activity(self, limit: int = 24) -> tuple[OperationsCenterItem, ...]:
        items: list[OperationsCenterItem] = []
        try:
            operations = self.runtime_operations.list_recent_operations(limit)
        except Exception:
            operations = []
        items.extend(self._operation_item(operation) for operation in operations)

        try:
            events = self.event_log.list_recent(limit)
        except Exception:
            events = []
        items.extend(self._event_item(event) for event in events)

        unique: dict[str, OperationsCenterItem] = {}
        for item in items:
            unique[item.item_id] = item
        return tuple(
            sorted(
                unique.values(),
                key=lambda item: item.occurred_at,
                reverse=True,
            )[: max(1, limit)]
        )

    def issue_items(self, limit: int = 24) -> tuple[OperationsCenterItem, ...]:
        try:
            events = self.event_log.list_recent(max(limit * 4, 40))
        except Exception:
            return ()
        issues = [
            self._event_item(event)
            for event in events
            if event.event_type in {"application.error", "application.notice"}
            and self._event_severity(event) in {"warning", "error", "critical"}
        ]
        return tuple(issues[: max(1, limit)])

    def _operation_item(self, operation: RuntimeOperation) -> OperationsCenterItem:
        screen, focus_key = _operation_target(operation.operation_kind)
        subject = operation.subject_id or operation.subject_kind
        summary_parts = [subject, operation.state]
        if operation.error_message:
            summary_parts.append(operation.error_message)
        severity = (
            "error"
            if operation.state in {"failed", "abandoned"}
            else "warning"
            if operation.state in {"cancelling", "cancelled"}
            else "active"
            if operation.state in {"starting", "running"}
            else "success"
        )
        operation_identity = operation.operation_kind or operation.operation_id
        subject_identity = operation.subject_id or operation.operation_id
        return OperationsCenterItem(
            item_id=f"operation:{operation.operation_id}",
            title=f"{operation_identity} · {subject_identity}",
            summary=" · ".join(part for part in summary_parts if part),
            status=operation.state,
            severity=severity,
            occurred_at=(
                operation.finished_at
                or operation.heartbeat_at
                or operation.started_at
            ),
            target_screen=screen,
            correlation_id=operation.correlation_id,
            operation_kind=operation.operation_kind,
            operation_state=operation.state,
            operation_subject=subject or operation.operation_id,
            operation_error=operation.error_message or "",
            focus_key=focus_key,
        )

    def _event_item(self, event: EventRecord) -> OperationsCenterItem:
        payload = _payload(event.payload_json)
        severity = self._event_severity(event)
        screen, focus_key = _event_target(event, payload)
        return OperationsCenterItem(
            item_id=f"event:{event.id}",
            title=_event_title(event, payload),
            summary=_event_summary(event, payload),
            status=severity,
            severity=severity,
            occurred_at=event.occurred_at,
            target_screen=screen,
            correlation_id=str(
                payload.get("correlation_id")
                or event.correlation_id
                or ""
            ),
            focus_key=focus_key,
        )

    @staticmethod
    def _event_severity(event: EventRecord) -> str:
        if event.event_type == "application.error":
            return "error"
        payload = _payload(event.payload_json)
        level = str(payload.get("level", "info")).casefold()
        if level in {"critical", "fatal"}:
            return "critical"
        if level == "error":
            return "error"
        if level == "warning":
            return "warning"
        return "info"


def _payload(raw: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _operation_target(kind: str) -> tuple[str, str]:
    return {
        "training": ("training", "focus.training.start"),
        "personality_test": ("tests", "focus.tests.build_portrait"),
        "analysis": ("analysis", ""),
        "inference": ("training", "focus.training.check_model"),
        "lineage_delete": ("agents", "focus.agents.delete_branch"),
    }.get(kind, ("dashboard", ""))


def _event_target(
    event: EventRecord,
    payload: dict[str, object],
) -> tuple[str, str]:
    component = str(payload.get("component", "")).casefold()
    entity = f"{event.entity_kind} {event.entity_id}".casefold()
    haystack = f"{component} {entity}"
    if "train" in haystack:
        return "training", ""
    if "experiment" in haystack or "portrait" in haystack or "test" in haystack:
        return "tests", "focus.tests.build_portrait"
    if "analysis" in haystack:
        return "analysis", ""
    if "dataset" in haystack:
        return "datasets", ""
    if "model_version" in haystack or "snapshot" in haystack:
        return "snapshots", ""
    if "lineage" in haystack or "agent" in haystack:
        return "agents", ""
    if "keybinding" in haystack:
        return "keybindings", ""
    return "dashboard", ""


def _event_title(event: EventRecord, payload: dict[str, object]) -> str:
    component = str(payload.get("component", "")).strip()
    if event.event_type == "application.error":
        error_type = str(payload.get("exception_type") or event.event_type).strip()
        return f"{error_type} · {component or event.entity_kind}"
    level = str(payload.get("level") or event.event_type).strip()
    return f"{level} · {component or event.entity_kind}"


def _event_summary(event: EventRecord, payload: dict[str, object]) -> str:
    message = str(
        payload.get("message")
        or payload.get("exception_message")
        or event.entity_id
        or event.event_type
    ).strip()
    error_id = str(payload.get("error_id", "")).strip()
    correlation = str(
        payload.get("correlation_id")
        or event.correlation_id
        or ""
    ).strip()
    suffix = " · ".join(part for part in (error_id, correlation) if part)
    return f"{message} · {suffix}" if suffix else message

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Mapping
from uuid import uuid4

from persona_training_lab.application.automation.execution import (
    AutomationExecution,
    AutomationProcessResult,
)
from persona_training_lab.application.ports.event_log import EventLogPort, EventRecord
from persona_training_lab.application.runtime.operations import ResourceClaim


AUTOMATION_AUDIT_SCHEMA = "ptl:automation-audit:v1"


@dataclass(slots=True)
class AutomationAuditTrail:
    event_log: EventLogPort

    def record_started(
        self,
        *,
        operation_id: str,
        correlation_id: str,
        operation_kind: str,
        subject_kind: str,
        subject_id: str,
        execution: AutomationExecution,
        claims: tuple[ResourceClaim, ...],
    ) -> None:
        self._append(
            event_type="automation.run.started",
            operation_id=operation_id,
            correlation_id=correlation_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            payload={
                "schema": AUTOMATION_AUDIT_SCHEMA,
                "phase": "started",
                "operation_kind": operation_kind,
                **self._execution_payload(execution, claims),
            },
        )

    def record_finished(
        self,
        *,
        operation_id: str,
        correlation_id: str,
        operation_kind: str,
        subject_kind: str,
        subject_id: str,
        execution: AutomationExecution,
        claims: tuple[ResourceClaim, ...],
        result: AutomationProcessResult,
        state: str,
    ) -> None:
        self._append(
            event_type="automation.run.finished",
            operation_id=operation_id,
            correlation_id=correlation_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            payload={
                "schema": AUTOMATION_AUDIT_SCHEMA,
                "phase": "finished",
                "operation_kind": operation_kind,
                "state": state,
                "return_code": result.return_code,
                "cancelled": result.cancelled,
                "timed_out": result.timed_out,
                "stdout_truncated": result.stdout_truncated,
                "stderr_truncated": result.stderr_truncated,
                **self._execution_payload(execution, claims),
            },
        )

    def record_blocked(
        self,
        *,
        operation_kind: str,
        subject_kind: str,
        subject_id: str,
        execution: AutomationExecution,
        claims: tuple[ResourceClaim, ...],
        detail: str,
    ) -> None:
        self._append(
            event_type="automation.run.blocked",
            operation_id="",
            correlation_id="",
            subject_kind=subject_kind,
            subject_id=subject_id,
            payload={
                "schema": AUTOMATION_AUDIT_SCHEMA,
                "phase": "blocked",
                "operation_kind": operation_kind,
                "detail": detail,
                **self._execution_payload(execution, claims),
            },
        )

    def record_launch_failed(
        self,
        *,
        operation_id: str,
        correlation_id: str,
        operation_kind: str,
        subject_kind: str,
        subject_id: str,
        execution: AutomationExecution,
        claims: tuple[ResourceClaim, ...],
        detail: str,
    ) -> None:
        self._append(
            event_type="automation.run.launch_failed",
            operation_id=operation_id,
            correlation_id=correlation_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            payload={
                "schema": AUTOMATION_AUDIT_SCHEMA,
                "phase": "launch_failed",
                "operation_kind": operation_kind,
                "detail": detail,
                **self._execution_payload(execution, claims),
            },
        )

    @staticmethod
    def _execution_payload(
        execution: AutomationExecution,
        claims: tuple[ResourceClaim, ...],
    ) -> dict[str, object]:
        command_snapshot = execution.command_snapshot
        command_json = json.dumps(
            command_snapshot,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return {
            "mode": execution.mode,
            "working_directory": str(execution.cwd),
            "command_sha256": sha256(command_json.encode("utf-8")).hexdigest(),
            "command_parts": len(command_snapshot),
            "environment_keys": tuple(sorted(execution.env)),
            "timeout_seconds": execution.timeout,
            "output_limit_bytes": execution.output_limit_bytes,
            "resource_claims": tuple(
                {
                    "kind": claim.resource_kind,
                    "id": claim.resource_id,
                    "access": claim.access_mode,
                }
                for claim in claims
            ),
        }

    def _append(
        self,
        *,
        event_type: str,
        operation_id: str,
        correlation_id: str,
        subject_kind: str,
        subject_id: str,
        payload: Mapping[str, object],
    ) -> None:
        event_payload = {
            "operation_id": operation_id,
            **dict(payload),
        }
        self.event_log.append(
            EventRecord(
                id=f"evt_{uuid4().hex[:12]}",
                event_type=event_type,
                entity_kind=subject_kind,
                entity_id=subject_id,
                payload_json=json.dumps(
                    event_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                ),
                occurred_at=datetime.now(timezone.utc).isoformat(),
                correlation_id=correlation_id or None,
                causation_id=operation_id or None,
            )
        )

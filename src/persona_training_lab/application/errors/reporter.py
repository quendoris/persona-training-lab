from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
from threading import RLock
from time import monotonic
import traceback
from typing import Any, Mapping
from uuid import uuid4

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.application.ports.event_log import EventLogPort, EventRecord


@dataclass(slots=True, frozen=True)
class ReportedError:
    error_id: str
    correlation_id: str
    user_message: UserMessage


class ApplicationErrorReporter:
    """Best-effort error reporting that must never break the application.

    Every incident gets a correlation id suitable for UI messages. Details are
    written to the rotating application log. The SQLite event log receives one
    record per duplicate window so a repeating failure cannot flood storage.
    """

    def __init__(
        self,
        event_log: EventLogPort | None = None,
        *,
        logger: logging.Logger | None = None,
        duplicate_window_seconds: float = 5.0,
    ) -> None:
        self._event_log = event_log
        self._logger = logger or logging.getLogger("persona_training_lab.errors")
        self._duplicate_window = max(0.0, duplicate_window_seconds)
        self._last_seen: dict[str, float] = {}
        self._lock = RLock()

    def capture(
        self,
        error: BaseException,
        *,
        component: str,
        user_message: UserMessage,
        entity_kind: str = "application",
        entity_id: str = "",
        operation_id: str = "",
        correlation_id: str = "",
        context: Mapping[str, Any] | None = None,
    ) -> ReportedError:
        error_id = f"err_{uuid4().hex[:12]}"
        correlation = correlation_id.strip() or f"corr_{uuid4().hex[:12]}"
        fingerprint = self._fingerprint(component, error)
        payload = {
            "error_id": error_id,
            "correlation_id": correlation,
            "component": component,
            "operation_id": operation_id,
            "exception_type": type(error).__name__,
            "exception_message": str(error),
            "traceback": "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )[-12_000:],
            "context": self._safe_context(context),
            "fingerprint": fingerprint,
        }
        self._write_log(payload)
        if self._should_persist(fingerprint):
            self._append_event(
                event_type="application.error",
                entity_kind=entity_kind or "application",
                entity_id=entity_id or operation_id or "global",
                correlation_id=correlation,
                payload=payload,
            )
        return ReportedError(error_id, correlation, user_message)

    def report_message(
        self,
        message: str,
        *,
        component: str,
        level: str = "WARNING",
        entity_kind: str = "application",
        entity_id: str = "",
        operation_id: str = "",
        correlation_id: str = "",
        context: Mapping[str, Any] | None = None,
    ) -> str:
        correlation = correlation_id.strip() or f"corr_{uuid4().hex[:12]}"
        fingerprint = sha256(
            f"{component}|{level}|{message}".encode("utf-8", errors="replace")
        ).hexdigest()
        payload = {
            "correlation_id": correlation,
            "component": component,
            "operation_id": operation_id,
            "level": level.upper(),
            "message": message,
            "context": self._safe_context(context),
            "fingerprint": fingerprint,
        }
        self._write_log(payload, level=level)
        if self._should_persist(fingerprint):
            self._append_event(
                event_type="application.notice",
                entity_kind=entity_kind or "application",
                entity_id=entity_id or operation_id or "global",
                correlation_id=correlation,
                payload=payload,
            )
        return correlation

    def _should_persist(self, fingerprint: str) -> bool:
        now = monotonic()
        with self._lock:
            previous = self._last_seen.get(fingerprint)
            self._last_seen[fingerprint] = now
            if previous is None:
                return True
            return now - previous >= self._duplicate_window

    def _append_event(
        self,
        *,
        event_type: str,
        entity_kind: str,
        entity_id: str,
        correlation_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        if self._event_log is None:
            return
        try:
            self._event_log.append(
                EventRecord(
                    id=f"evt_{uuid4().hex[:12]}",
                    event_type=event_type,
                    entity_kind=entity_kind,
                    entity_id=entity_id,
                    correlation_id=correlation_id,
                    causation_id=None,
                    payload_json=json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        default=str,
                    ),
                    occurred_at=datetime.now(timezone.utc).isoformat(),
                )
            )
        except Exception:
            # Reporting failure is deliberately swallowed; the original workflow
            # must remain usable even when the event-log storage is unavailable.
            self._logger.debug(
                "Failed to append structured error event",
                exc_info=True,
            )

    def _write_log(
        self,
        payload: Mapping[str, Any],
        *,
        level: str = "ERROR",
    ) -> None:
        try:
            log_level = getattr(logging, level.upper(), logging.ERROR)
            self._logger.log(
                log_level,
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                ),
            )
        except Exception:
            return

    @staticmethod
    def _fingerprint(component: str, error: BaseException) -> str:
        raw = f"{component}|{type(error).__name__}|{error}"
        return sha256(raw.encode("utf-8", errors="replace")).hexdigest()

    @staticmethod
    def _safe_context(context: Mapping[str, Any] | None) -> dict[str, Any]:
        if not context:
            return {}
        result: dict[str, Any] = {}
        for key, value in context.items():
            clean_key = str(key)
            if any(
                token in clean_key.casefold()
                for token in ("password", "secret", "token", "api_key", "key_material")
            ):
                result[clean_key] = "<redacted>"
                continue
            try:
                json.dumps(value, default=str)
                result[clean_key] = value
            except Exception:
                result[clean_key] = repr(value)
        return result

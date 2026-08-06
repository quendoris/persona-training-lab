from __future__ import annotations

from persona_training_lab.application.operations_center import OperationsCenterItem
from persona_training_lab.ui.i18n.manager import LocalizationManager


_OPERATION_KIND_KEYS: dict[str, str] = {
    "training": "operations.kind.training",
    "personality_test": "operations.kind.personality_test",
    "analysis": "operations.kind.analysis",
    "inference": "operations.kind.inference",
    "lineage_delete": "operations.kind.lineage_delete",
}

_OPERATION_STATE_KEYS: dict[str, str] = {
    "starting": "operations.state.starting",
    "running": "operations.state.running",
    "cancelling": "operations.state.cancelling",
    "succeeded": "operations.state.succeeded",
    "failed": "operations.state.failed",
    "cancelled": "operations.state.cancelled",
    "abandoned": "operations.state.abandoned",
}

_SEVERITY_KEYS: dict[str, str] = {
    "active": "operations.severity.active",
    "success": "operations.severity.success",
    "info": "operations.severity.info",
    "warning": "operations.severity.warning",
    "error": "operations.severity.error",
    "critical": "operations.severity.critical",
}


def text(
    localization: LocalizationManager | None,
    key: str,
    fallback: str,
    *,
    count: int | None = None,
    **values: object,
) -> str:
    if localization is None:
        return fallback.format_map(values) if values else fallback
    return localization.text(key, count=count, **values)


def item_title(
    item: OperationsCenterItem,
    localization: LocalizationManager | None,
) -> str:
    if not item.operation_kind:
        return item.title
    operation = text(
        localization,
        _OPERATION_KIND_KEYS.get(
            item.operation_kind,
            "operations.kind.generic",
        ),
        item.operation_kind.replace("_", " ").title() or "Операция",
    )
    return text(
        localization,
        "operations.item.title",
        "{operation} · {subject}",
        operation=operation,
        subject=item.operation_subject,
    )


def item_summary(
    item: OperationsCenterItem,
    localization: LocalizationManager | None,
) -> str:
    if not item.operation_kind:
        return item.summary
    state = item_status(item, localization)
    summary = text(
        localization,
        "operations.item.summary",
        "{subject} · {state}",
        subject=item.operation_subject,
        state=state,
    )
    if item.operation_error:
        return text(
            localization,
            "operations.item.summary_with_error",
            "{summary} · {error}",
            summary=summary,
            error=item.operation_error,
        )
    return summary


def item_status(
    item: OperationsCenterItem,
    localization: LocalizationManager | None,
) -> str:
    if item.operation_state:
        return text(
            localization,
            _OPERATION_STATE_KEYS.get(
                item.operation_state,
                "operations.state.unknown",
            ),
            item.status or item.operation_state,
        )
    return text(
        localization,
        _SEVERITY_KEYS.get(item.severity, "operations.severity.info"),
        item.status,
    )


def item_focus(
    item: OperationsCenterItem,
    localization: LocalizationManager | None,
) -> str:
    if not item.focus_key:
        return item.focus_text
    return text(localization, item.focus_key, item.focus_text)

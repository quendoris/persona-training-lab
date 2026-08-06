from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from persona_training_lab.application.operations_center import OperationsCenterItem
from persona_training_lab.i18n.catalog import LocaleCatalog
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


@lru_cache(maxsize=1)
def _base_catalog() -> LocaleCatalog:
    path = Path(
        str(
            files("persona_training_lab.i18n").joinpath(
                "catalogs",
                "ru-RU.json",
            )
        )
    )
    return LocaleCatalog.load(path)


def text(
    localization: LocalizationManager | None,
    key: str,
    *,
    count: int | None = None,
    **values: object,
) -> str:
    if localization is not None:
        return localization.text(key, count=count, **values)
    return _base_catalog().text(key, count=count, values=values)


def item_title(
    item: OperationsCenterItem,
    localization: LocalizationManager | None,
) -> str:
    if not item.operation_kind:
        return item.title
    key = _OPERATION_KIND_KEYS.get(
        item.operation_kind,
        "operations.kind.generic",
    )
    operation = text(
        localization,
        key,
        kind=item.operation_kind.replace("_", " ").title(),
    )
    return text(
        localization,
        "operations.item.title",
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
        subject=item.operation_subject,
        state=state,
    )
    if item.operation_error:
        return text(
            localization,
            "operations.item.summary_with_error",
            summary=summary,
            error=item.operation_error,
        )
    return summary


def item_status(
    item: OperationsCenterItem,
    localization: LocalizationManager | None,
) -> str:
    if item.operation_state:
        key = _OPERATION_STATE_KEYS.get(
            item.operation_state,
            "operations.state.unknown",
        )
        return text(
            localization,
            key,
            state=item.operation_state,
        )
    return text(
        localization,
        _SEVERITY_KEYS.get(item.severity, "operations.severity.info"),
    )


def item_focus(
    item: OperationsCenterItem,
    localization: LocalizationManager | None,
) -> str:
    if not item.focus_key:
        return item.focus_text
    return text(localization, item.focus_key)

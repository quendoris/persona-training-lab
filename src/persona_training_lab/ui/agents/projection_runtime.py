from __future__ import annotations

from collections.abc import Mapping

from persona_training_lab.application.errors.reporter import (
    ApplicationErrorReporter,
)
from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.refresh_worker import LineageRefreshFailure


class ProjectionSafetyBinding:
    """Synchronize persisted safety links without making QWidget own state."""

    def __init__(self, safety: LineageRuntimeSafety | None) -> None:
        self._safety = safety
        self._bound_node_ids: tuple[str, ...] | None = None

    @property
    def bound_node_ids(self) -> tuple[str, ...] | None:
        return self._bound_node_ids

    def reconcile(
        self,
        resources: Mapping[str, tuple[ResourceClaim, ...]],
        *,
        snapshot_proven: bool,
    ) -> tuple[str, ...] | None:
        safety = self._safety
        if safety is None or not snapshot_proven:
            return self._bound_node_ids
        self._bound_node_ids = safety.reconcile_projection(
            resources,
            self._bound_node_ids,
        )
        return self._bound_node_ids


class LineageRefreshIncidentReporter:
    """Convert worker failures into throttled application incidents."""

    def __init__(self, reporter: ApplicationErrorReporter | None) -> None:
        self._reporter = reporter

    def report(
        self,
        failure: LineageRefreshFailure,
        *,
        last_good_available: bool,
    ) -> str:
        reporter = self._reporter
        if reporter is None:
            return ""
        return reporter.report_message(
            "Lineage refresh failed: "
            f"{failure.error_type}: {failure.message}",
            component="ui.agents.lineage_refresh",
            level="ERROR",
            entity_kind="lineage_refresh",
            entity_id=str(failure.generation),
            context={
                "generation": failure.generation,
                "error_type": failure.error_type,
                "traceback": failure.traceback_text,
                "last_good_available": last_good_available,
            },
        )

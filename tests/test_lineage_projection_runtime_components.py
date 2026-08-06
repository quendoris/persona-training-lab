from __future__ import annotations

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.projection_runtime import (
    LineageRefreshIncidentReporter,
    ProjectionSafetyBinding,
)
from persona_training_lab.ui.agents.refresh_worker import LineageRefreshFailure


class _SafetySpy:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object]] = []

    def reconcile_projection(self, resources, previous_node_ids):
        self.calls.append((resources, previous_node_ids))
        return tuple(sorted(resources))


class _ReporterSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def report_message(self, message: str, **kwargs) -> str:
        self.calls.append((message, kwargs))
        return "corr_lineage_001"


def _failure() -> LineageRefreshFailure:
    return LineageRefreshFailure(
        generation=17,
        error_type="OperationalError",
        message="database is busy",
        traceback_text="traceback payload",
    )


def test_safety_binding_never_mutates_registry_for_unproven_snapshot() -> None:
    safety = _SafetySpy()
    binding = ProjectionSafetyBinding(safety)  # type: ignore[arg-type]

    result = binding.reconcile(
        {
            "snapshot": (
                ResourceClaim("model_version", "mdl_001", "read"),
            ),
        },
        snapshot_proven=False,
    )

    assert result is None
    assert binding.bound_node_ids is None
    assert safety.calls == []


def test_safety_binding_threads_previous_projection_ids_between_refreshes() -> None:
    safety = _SafetySpy()
    binding = ProjectionSafetyBinding(safety)  # type: ignore[arg-type]
    first = {
        "snapshot": (
            ResourceClaim("model_version", "mdl_001", "read"),
        ),
    }
    second = {
        "training": (
            ResourceClaim("training_run", "trn_002", "read"),
        ),
    }

    assert binding.reconcile(first, snapshot_proven=True) == ("snapshot",)
    assert binding.reconcile(second, snapshot_proven=True) == ("training",)
    assert safety.calls == [
        (first, None),
        (second, ("snapshot",)),
    ]


def test_incident_reporter_is_optional_and_side_effect_free_when_absent() -> None:
    reporter = LineageRefreshIncidentReporter(None)

    assert reporter.report(_failure(), last_good_available=True) == ""


def test_incident_reporter_preserves_generation_traceback_and_last_good() -> None:
    spy = _ReporterSpy()
    reporter = LineageRefreshIncidentReporter(spy)  # type: ignore[arg-type]

    correlation = reporter.report(
        _failure(),
        last_good_available=True,
    )

    assert correlation == "corr_lineage_001"
    assert len(spy.calls) == 1
    message, kwargs = spy.calls[0]
    assert message == (
        "Lineage refresh failed: OperationalError: database is busy"
    )
    assert kwargs["component"] == "ui.agents.lineage_refresh"
    assert kwargs["level"] == "ERROR"
    assert kwargs["entity_kind"] == "lineage_refresh"
    assert kwargs["entity_id"] == "17"
    assert kwargs["context"] == {
        "generation": 17,
        "error_type": "OperationalError",
        "traceback": "traceback payload",
        "last_good_available": True,
    }

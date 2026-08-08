from __future__ import annotations

from persona_training_lab.ui.agents.lineage_presentation import (
    LineagePresentationProjection,
)
from persona_training_lab.ui.agents.lineage_projection_adapter import (
    build_atomic_lineage,
)
from persona_training_lab.ui.agents.lineage_projection_legacy import (
    build_legacy_lineage,
)


def build_lineage_projection(view_model) -> LineagePresentationProjection:
    """Resolve the modern atomic projection, falling back only for legacy VMs."""

    snapshot_builder = getattr(view_model, "build_lineage_snapshot", None)
    if callable(snapshot_builder):
        return build_atomic_lineage(snapshot_builder())
    return build_legacy_lineage(view_model)


__all__ = ("build_lineage_projection",)

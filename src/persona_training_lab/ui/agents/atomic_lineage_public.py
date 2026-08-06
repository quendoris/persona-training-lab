from __future__ import annotations

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageSnapshot,
)
from persona_training_lab.ui.agents.atomic_lineage import (
    _build_canvas_projection,
)
from persona_training_lab.ui.agents.real_lineage import RealLineageProjection


def build_atomic_lineage(
    snapshot: AtomicLineageSnapshot,
) -> RealLineageProjection:
    """Build the immutable canvas projection from one atomic source snapshot."""

    return _build_canvas_projection(snapshot)

from __future__ import annotations

from persona_training_lab.ui.agents.lineage_projection_adapter import (
    build_atomic_lineage,
)
from persona_training_lab.ui.agents.lineage_projection_resolver import (
    build_lineage_projection,
)

build_real_lineage = build_lineage_projection
_build_canvas_projection = build_atomic_lineage

__all__ = ("build_real_lineage",)

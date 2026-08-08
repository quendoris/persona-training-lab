from __future__ import annotations

from persona_training_lab.ui.agents.lineage_presentation import (
    LineagePresentationProjection,
    ProjectedVersionNode,
    RealLineageProjection,
)
from persona_training_lab.ui.agents.lineage_projection_legacy import (
    build_legacy_lineage,
)

build_real_lineage = build_legacy_lineage

__all__ = (
    "LineagePresentationProjection",
    "ProjectedVersionNode",
    "RealLineageProjection",
    "build_real_lineage",
)

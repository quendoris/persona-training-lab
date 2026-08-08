from __future__ import annotations

from persona_training_lab.ui.agents.version_graph_clean_layout import (
    VersionGraphCanvas as CleanLayoutVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_curved import (
    VersionGraphCanvas as CurvedVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_free_zoom import (
    VersionGraphCanvas as FreeZoomVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_stateful import (
    VersionGraphCanvas as StatefulVersionGraphCanvas,
)


def test_stateful_layer_has_no_shadow_layout_algorithm() -> None:
    retired_stateful_methods = {
        "_lanes",
        "_branch_groups",
        "_collect_branch_ids",
        "_choose_free_lane",
        "_candidate_lanes",
        "_lane_offsets",
        "_lane_is_free",
    }

    assert retired_stateful_methods.isdisjoint(StatefulVersionGraphCanvas.__dict__)
    assert StatefulVersionGraphCanvas._lanes is CurvedVersionGraphCanvas._lanes
    assert FreeZoomVersionGraphCanvas._lanes is CleanLayoutVersionGraphCanvas._lanes
    assert (
        FreeZoomVersionGraphCanvas._lane_offsets
        is CleanLayoutVersionGraphCanvas._lane_offsets
    )

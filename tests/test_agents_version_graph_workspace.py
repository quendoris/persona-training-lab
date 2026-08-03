from __future__ import annotations

from persona_training_lab.ui.agents.version_graph_workspace import (
    WorkspaceBounds,
    build_workspace_geometry,
    grow_workspace_geometry,
)


def test_workspace_size_follows_content_with_large_symmetric_margins() -> None:
    geometry = build_workspace_geometry(
        WorkspaceBounds(left=-400.0, top=-100.0, right=900.0, bottom=700.0),
        horizontal_margin=1800.0,
        vertical_margin=1100.0,
        minimum_width=3200.0,
        minimum_height=2400.0,
    )

    assert geometry.origin_x == 2200.0
    assert geometry.origin_y == 1200.0
    assert geometry.width == 4900.0
    assert geometry.height == 3000.0


def test_workspace_respects_minimum_editing_area_for_small_trees() -> None:
    geometry = build_workspace_geometry(
        WorkspaceBounds(left=-20.0, top=-20.0, right=80.0, bottom=80.0),
        horizontal_margin=600.0,
        vertical_margin=400.0,
        minimum_width=2400.0,
        minimum_height=1600.0,
    )

    assert geometry.width == 2400.0
    assert geometry.height == 1600.0
    assert geometry.origin_x == 620.0
    assert geometry.origin_y == 420.0


def test_drag_growth_never_moves_existing_workspace_origin() -> None:
    original = build_workspace_geometry(
        WorkspaceBounds(left=0.0, top=0.0, right=500.0, bottom=500.0),
        horizontal_margin=1000.0,
        vertical_margin=700.0,
        minimum_width=2400.0,
        minimum_height=1800.0,
    )

    grown = grow_workspace_geometry(
        original,
        WorkspaceBounds(left=-200.0, top=-100.0, right=2600.0, bottom=1900.0),
        horizontal_margin=1000.0,
        vertical_margin=700.0,
    )

    assert grown.origin_x == original.origin_x
    assert grown.origin_y == original.origin_y
    assert grown.width > original.width
    assert grown.height > original.height

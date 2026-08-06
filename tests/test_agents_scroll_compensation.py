from __future__ import annotations

from persona_training_lab.ui.agents.scroll_compensation import (
    ScrollPosition,
    WorkspaceScrollCompensator,
)


def test_zoom_compensation_keeps_pointer_anchor_stable() -> None:
    target = WorkspaceScrollCompensator.zoom_target(
        ScrollPosition(120, 80),
        anchor_x=200.0,
        anchor_y=100.0,
        old_zoom=1.0,
        new_zoom=1.5,
    )

    assert target == ScrollPosition(220, 130)


def test_zoom_compensation_rejects_nonpositive_previous_zoom() -> None:
    assert (
        WorkspaceScrollCompensator.zoom_target(
            ScrollPosition(10, 20),
            anchor_x=100.0,
            anchor_y=100.0,
            old_zoom=0.0,
            new_zoom=1.0,
        )
        is None
    )


def test_zoom_compensation_rounds_each_axis_without_accumulated_state() -> None:
    current = ScrollPosition(17, 19)

    first = WorkspaceScrollCompensator.zoom_target(
        current,
        anchor_x=3.0,
        anchor_y=5.0,
        old_zoom=1.0,
        new_zoom=1.25,
    )
    second = WorkspaceScrollCompensator.zoom_target(
        current,
        anchor_x=3.0,
        anchor_y=5.0,
        old_zoom=1.0,
        new_zoom=1.25,
    )

    assert first == ScrollPosition(18, 20)
    assert second == first


def test_origin_shift_compensation_uses_current_scroll_position() -> None:
    target = WorkspaceScrollCompensator.origin_shift_target(
        ScrollPosition(310, 205),
        delta_x=-12.4,
        delta_y=7.6,
    )

    assert target == ScrollPosition(298, 213)

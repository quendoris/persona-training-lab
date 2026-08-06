from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScrollPosition:
    horizontal: int
    vertical: int


class WorkspaceScrollCompensator:
    """Calculate stable scroll targets for zoom and workspace origin changes."""

    @staticmethod
    def zoom_target(
        current: ScrollPosition,
        *,
        anchor_x: float,
        anchor_y: float,
        old_zoom: float,
        new_zoom: float,
    ) -> ScrollPosition | None:
        if old_zoom <= 0:
            return None
        ratio = new_zoom / old_zoom
        return ScrollPosition(
            horizontal=current.horizontal
            + int(round(anchor_x * (ratio - 1.0))),
            vertical=current.vertical
            + int(round(anchor_y * (ratio - 1.0))),
        )

    @staticmethod
    def origin_shift_target(
        current: ScrollPosition,
        *,
        delta_x: float,
        delta_y: float,
    ) -> ScrollPosition:
        return ScrollPosition(
            horizontal=current.horizontal + int(round(delta_x)),
            vertical=current.vertical + int(round(delta_y)),
        )


__all__ = ("ScrollPosition", "WorkspaceScrollCompensator")

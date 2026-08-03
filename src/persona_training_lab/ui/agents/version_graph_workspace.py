from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkspaceBounds:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)


@dataclass(frozen=True, slots=True)
class WorkspaceGeometry:
    origin_x: float
    origin_y: float
    width: float
    height: float


def build_workspace_geometry(
    bounds: WorkspaceBounds,
    *,
    horizontal_margin: float,
    vertical_margin: float,
    minimum_width: float,
    minimum_height: float,
) -> WorkspaceGeometry:
    """Place current content inside a large, symmetric editable workspace."""

    width = max(minimum_width, bounds.width + horizontal_margin * 2.0)
    height = max(minimum_height, bounds.height + vertical_margin * 2.0)
    return WorkspaceGeometry(
        origin_x=horizontal_margin - bounds.left,
        origin_y=vertical_margin - bounds.top,
        width=width,
        height=height,
    )


def grow_workspace_geometry(
    geometry: WorkspaceGeometry,
    bounds: WorkspaceBounds,
    *,
    horizontal_margin: float,
    vertical_margin: float,
) -> WorkspaceGeometry:
    """Grow right/down during a drag without moving the existing canvas origin."""

    required_width = bounds.right + geometry.origin_x + horizontal_margin
    required_height = bounds.bottom + geometry.origin_y + vertical_margin
    return WorkspaceGeometry(
        origin_x=geometry.origin_x,
        origin_y=geometry.origin_y,
        width=max(geometry.width, required_width),
        height=max(geometry.height, required_height),
    )

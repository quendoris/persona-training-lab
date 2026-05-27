from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication


@dataclass(slots=True, frozen=True)
class UiDensity:
    scale: float
    name: str
    screen_width: int
    screen_height: int
    window_width: int
    window_height: int
    sidebar_width: int
    right_dock_width: int
    bottom_dock_height: int
    root_margin: int
    root_spacing: int


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_ui_scale(width: int, height: int) -> tuple[float, str]:
    """Return a density scale from available screen geometry.

    Height is the main driver because bottom docks and large cards are the
    first thing that make the app unusable on notebooks. Width still matters:
    compact notebooks should not keep the desktop sidebar/card density.
    """
    if height <= 760 or width <= 1366:
        return 0.78, "compact-xs"
    if height <= 850 or width <= 1440:
        return 0.84, "compact"
    if height <= 950 or width <= 1600:
        return 0.90, "dense"
    if height <= 1080:
        return 0.94, "balanced"
    if height <= 1250:
        return 1.0, "comfortable"
    return 1.05, "large"


def screen_density() -> UiDensity:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        width, height = 1440, 900
    else:
        geometry = screen.availableGeometry()
        width, height = geometry.width(), geometry.height()
    scale, name = compute_ui_scale(width, height)

    window_width = int(_clamp(width * 0.92, 1020, min(width, 1680)))
    window_height = int(_clamp(height * 0.90, 680, min(height, 1040)))
    return UiDensity(
        scale=scale,
        name=name,
        screen_width=width,
        screen_height=height,
        window_width=window_width,
        window_height=window_height,
        sidebar_width=scaled(320, scale, minimum=248, maximum=330),
        right_dock_width=scaled(310, scale, minimum=240, maximum=320),
        bottom_dock_height=scaled(250, scale, minimum=165, maximum=260),
        root_margin=scaled(14, scale, minimum=8, maximum=16),
        root_spacing=scaled(16, scale, minimum=8, maximum=18),
    )


def scaled(value: int | float, scale: float | None = None, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if scale is None:
        scale = current_scale()
    result = int(round(float(value) * float(scale)))
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def current_scale(default: float = 1.0) -> float:
    app = QApplication.instance()
    if app is None:
        return default
    value = app.property("ptl_ui_scale")
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def apply_density(app: QApplication) -> UiDensity:
    density = screen_density()
    app.setProperty("ptl_ui_scale", density.scale)
    app.setProperty("ptl_ui_density", density.name)
    app.setProperty("ptl_screen_width", density.screen_width)
    app.setProperty("ptl_screen_height", density.screen_height)
    return density

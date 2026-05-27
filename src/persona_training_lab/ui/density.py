from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication


MIN_UI_SCALE = 0.68
MAX_UI_SCALE = 1.12


@dataclass(slots=True, frozen=True)
class UiDensity:
    scale: float
    auto_scale: float
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
    is_manual: bool = False


@dataclass(slots=True, frozen=True)
class ScreenGeometry:
    width: int
    height: int


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _coerce_manual_scale(value: str | float | None) -> float | None:
    if value in (None, "", "auto"):
        return None
    try:
        return _clamp(float(value), MIN_UI_SCALE, MAX_UI_SCALE)
    except (TypeError, ValueError):
        return None


def compute_ui_scale(width: int, height: int) -> tuple[float, str]:
    """Return the automatic density scale from available screen geometry."""
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


def screen_geometry() -> ScreenGeometry:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return ScreenGeometry(1440, 900)
    geometry = screen.availableGeometry()
    return ScreenGeometry(geometry.width(), geometry.height())


def density_for_geometry(width: int, height: int, manual_scale: str | float | None = None) -> UiDensity:
    auto_scale, auto_name = compute_ui_scale(width, height)
    resolved_manual = _coerce_manual_scale(manual_scale)
    scale = resolved_manual if resolved_manual is not None else auto_scale
    name = f"manual {int(round(scale * 100))}%" if resolved_manual is not None else auto_name

    window_width = int(_clamp(width * 0.92, 980, min(width, 1680)))
    window_height = int(_clamp(height * 0.90, 620, min(height, 1040)))
    return UiDensity(
        scale=scale,
        auto_scale=auto_scale,
        name=name,
        screen_width=width,
        screen_height=height,
        window_width=window_width,
        window_height=window_height,
        sidebar_width=scaled(320, scale, minimum=220, maximum=330),
        right_dock_width=scaled(310, scale, minimum=220, maximum=320),
        bottom_dock_height=scaled(250, scale, minimum=140, maximum=260),
        root_margin=scaled(14, scale, minimum=6, maximum=16),
        root_spacing=scaled(16, scale, minimum=6, maximum=18),
        is_manual=resolved_manual is not None,
    )


def screen_density(manual_scale: str | float | None = None) -> UiDensity:
    geometry = screen_geometry()
    return density_for_geometry(geometry.width, geometry.height, manual_scale)


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


def apply_density(app: QApplication, manual_scale: str | float | None = None) -> UiDensity:
    density = screen_density(manual_scale)
    app.setProperty("ptl_ui_scale", density.scale)
    app.setProperty("ptl_ui_auto_scale", density.auto_scale)
    app.setProperty("ptl_ui_density", density.name)
    app.setProperty("ptl_ui_scale_manual", density.is_manual)
    app.setProperty("ptl_screen_width", density.screen_width)
    app.setProperty("ptl_screen_height", density.screen_height)
    return density

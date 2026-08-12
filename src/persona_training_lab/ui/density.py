from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QApplication


MIN_UI_SCALE = 0.68
MAX_UI_SCALE = 1.12
_SCALE_BEGIN = "/* PTL_UI_SCALE_BEGIN */"
_SCALE_END = "/* PTL_UI_SCALE_END */"
_SCALE_DEBOUNCE_MS = 140


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
    if value is None:
        return None
    if isinstance(value, str) and value in ("", "auto"):
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


def _strip_scale_block(stylesheet: str) -> str:
    start = stylesheet.find(_SCALE_BEGIN)
    end = stylesheet.find(_SCALE_END)
    if start == -1 or end == -1 or end < start:
        return stylesheet
    return stylesheet[:start].rstrip() + "\n" + stylesheet[end + len(_SCALE_END):].lstrip()


def build_scale_stylesheet(scale: float) -> str:
    s = _clamp(scale, MIN_UI_SCALE, MAX_UI_SCALE)
    px = lambda value, low=None, high=None: scaled(value, s, minimum=low, maximum=high)  # noqa: E731
    return f"""
{_SCALE_BEGIN}
QWidget {{ font-size: {px(13, 9, 14)}px; }}
QLabel#ScreenTitle {{ font-size: {px(28, 18, 30)}px; }}
QLabel#SectionTitle {{ font-size: {px(17, 12, 18)}px; }}
QLabel#SidebarTitle {{ font-size: {px(16, 12, 17)}px; }}
QLabel#CardTitle {{ font-size: {px(14, 10, 15)}px; }}
QLabel#MetricValue {{ font-size: {px(30, 18, 32)}px; }}
QPushButton#NavButton {{ min-height: {px(46, 30, 50)}px; border-radius: {px(18, 12, 20)}px; }}
QPushButton#ThemeChip {{ padding: {px(8, 4, 9)}px {px(12, 6, 13)}px; }}
QPushButton#SidebarMenuButton {{ min-height: {px(20, 16, 22)}px; padding: {px(4, 2, 5)}px {px(14, 8, 15)}px; }}
QPushButton {{ padding: {px(12, 6, 13)}px {px(16, 8, 17)}px; border-radius: {px(16, 10, 18)}px; }}
QListWidget, QTextEdit, QPlainTextEdit, QComboBox, QLineEdit {{ padding: {px(8, 4, 9)}px; border-radius: {px(16, 10, 18)}px; }}
QComboBox::drop-down {{ width: {px(26, 18, 28)}px; }}
QLabel#WorkflowPill {{ padding: {px(10, 5, 11)}px {px(12, 6, 13)}px; }}
QDockWidget::title {{ padding: {px(8, 4, 9)}px {px(10, 6, 11)}px; }}
QLabel#TelemetryChip {{ padding: {px(5, 2, 6)}px {px(10, 5, 11)}px; font-size: {px(11, 9, 12)}px; }}
QLabel#TelemetryCaption {{ font-size: {px(11, 9, 12)}px; }}
{_SCALE_END}
"""


def _apply_scaled_styles_now(app: QApplication, scale: float) -> None:
    resolved = _clamp(scale, MIN_UI_SCALE, MAX_UI_SCALE)
    font = QFont(app.font())
    font.setPointSizeF(_clamp(10.0 * resolved, 8.0, 11.5))
    app.setFont(font)

    base = _strip_scale_block(app.styleSheet())
    app.setStyleSheet(base.rstrip() + "\n" + build_scale_stylesheet(resolved))
    app.setProperty("ptl_ui_last_applied_scale", resolved)


def _scale_timer(app: QApplication) -> QTimer:
    timer = app.property("ptl_ui_scale_timer")
    if isinstance(timer, QTimer):
        return timer

    timer = QTimer(app)
    timer.setSingleShot(True)

    def flush() -> None:
        pending = app.property("ptl_ui_pending_scale")
        try:
            resolved = float(pending)
        except (TypeError, ValueError):
            resolved = current_scale()
        _apply_scaled_styles_now(app, resolved)

    timer.timeout.connect(flush)
    app.setProperty("ptl_ui_scale_timer", timer)
    return timer


def apply_scaled_styles(app: QApplication, scale: float | None = None, *, immediate: bool = False) -> None:
    """Apply global scale overrides.

    Slider movement can emit many valueChanged signals per second. Rebuilding
    the full Qt stylesheet on every signal is expensive, so normal calls are
    coalesced. Startup, theme changes, auto reset and slider release can request
    immediate=True.
    """
    resolved = current_scale() if scale is None else _clamp(float(scale), MIN_UI_SCALE, MAX_UI_SCALE)
    app.setProperty("ptl_ui_pending_scale", resolved)

    if immediate:
        timer = app.property("ptl_ui_scale_timer")
        if isinstance(timer, QTimer):
            timer.stop()
        _apply_scaled_styles_now(app, resolved)
        return

    _scale_timer(app).start(_SCALE_DEBOUNCE_MS)


def apply_density(app: QApplication, manual_scale: str | float | None = None) -> UiDensity:
    density = screen_density(manual_scale)
    app.setProperty("ptl_ui_scale", density.scale)
    app.setProperty("ptl_ui_auto_scale", density.auto_scale)
    app.setProperty("ptl_ui_density", density.name)
    app.setProperty("ptl_ui_scale_manual", density.is_manual)
    app.setProperty("ptl_screen_width", density.screen_width)
    app.setProperty("ptl_screen_height", density.screen_height)
    apply_scaled_styles(app, density.scale, immediate=True)
    return density

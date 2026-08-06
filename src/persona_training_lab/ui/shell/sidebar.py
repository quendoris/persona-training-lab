from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, Signal, QRect, QRectF
from PySide6.QtGui import QColor, QCursor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.i18n.catalog import LocaleCatalog
from persona_training_lab.ui.density import (
    MAX_UI_SCALE,
    MIN_UI_SCALE,
    apply_scaled_styles,
    current_scale,
)
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.themes.tokens import ACCENTS, THEMES
from persona_training_lab.ui.viewmodels.style import StyleViewModel

SIDEBAR_ICON_RENDER_SIZE = 18
SIDEBAR_ICON_BADGE_LEFT = 22
SIDEBAR_ICON_BADGE_SIZE = 30
SIDEBAR_TEXT_LEFT_PADDING = 70


@lru_cache(maxsize=1)
def _base_catalog() -> LocaleCatalog:
    path = Path(
        str(
            files("persona_training_lab.i18n").joinpath(
                "catalogs",
                "ru-RU.json",
            )
        )
    )
    return LocaleCatalog.load(path)


def base_text(key: str, **values: object) -> str:
    """Resolve shell text when the standalone base sidebar has no manager."""

    return _base_catalog().text(key, values=values)


def _custom_accent_palette(hex_color: str) -> dict[str, str]:
    color = QColor(hex_color)
    if not color.isValid():
        color = QColor(ACCENTS["cyan"]["accent"])
    return {
        "accent": color.name(),
        "accent_soft_dark": color.darker(300).name(),
        "accent_soft_light": color.lighter(195).name(),
    }


def _icons_root() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "icons"


def _render_svg_icon(
    path: Path,
    color: str,
    canvas_size: int,
    icon_size: int,
    *,
    offset_x: int = 0,
    tight_crop: bool = False,
) -> QPixmap:
    if not path.exists():
        return QPixmap()

    raw = path.read_text(encoding="utf-8")
    themed = (
        raw.replace("currentColor", color)
        .replace("currentcolor", color)
        .replace("#000000", color)
        .replace("#000", color)
        .replace("black", color)
    )

    renderer = QSvgRenderer(QByteArray(themed.encode("utf-8")))
    pixmap = QPixmap(canvas_size, canvas_size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    view_box = renderer.viewBoxF()
    if view_box.width() > 0 and view_box.height() > 0:
        scale = min(icon_size / view_box.width(), icon_size / view_box.height())
        target_w = round(view_box.width() * scale)
        target_h = round(view_box.height() * scale)
    else:
        target_w = icon_size
        target_h = icon_size

    target_x = round((canvas_size - target_w) / 2)
    max_target_x = max(0, canvas_size - target_w)
    target_x = max(0, min(target_x, max_target_x))
    target_y = round((canvas_size - target_h) / 2)
    target = QRectF(target_x, target_y, target_w, target_h)
    renderer.render(painter, target)

    painter.end()
    if not tight_crop:
        shifted_x = max(0, min(target_x + offset_x, max_target_x))
        if shifted_x == target_x:
            return pixmap
        shifted = QPixmap(canvas_size, canvas_size)
        shifted.fill(Qt.GlobalColor.transparent)
        shifted_painter = QPainter(shifted)
        shifted_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        shifted_painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform,
            True,
        )
        shifted_painter.drawPixmap(
            shifted_x,
            target_y,
            pixmap.copy(target.toRect()),
        )
        shifted_painter.end()
        return shifted

    image = pixmap.toImage()
    min_x, min_y = canvas_size, canvas_size
    max_x, max_y = -1, -1
    for y in range(canvas_size):
        for x in range(canvas_size):
            if image.pixelColor(x, y).alpha() > 0:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if max_x < min_x or max_y < min_y:
        return pixmap

    bounds = QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    cropped = pixmap.copy(bounds)

    final_pixmap = QPixmap(canvas_size, canvas_size)
    final_pixmap.fill(Qt.GlobalColor.transparent)
    final_painter = QPainter(final_pixmap)
    final_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    final_painter.setRenderHint(
        QPainter.RenderHint.SmoothPixmapTransform,
        True,
    )

    max_crop_x = max(0, canvas_size - cropped.width())
    final_x = max(
        0,
        min(
            round((canvas_size - cropped.width()) / 2) + offset_x,
            max_crop_x,
        ),
    )
    final_y = max(
        0,
        min(
            round((canvas_size - cropped.height()) / 2),
            canvas_size - cropped.height(),
        ),
    )
    final_painter.drawPixmap(final_x, final_y, cropped)
    final_painter.end()
    return final_pixmap


class NavButton(QPushButton):
    def __init__(self, screen_id: str, icon_text: str, title: str) -> None:
        super().__init__(title)
        self.screen_id = screen_id
        self._fallback_icon_text = icon_text
        self._icon_path = _icons_root() / "sidebar" / f"{screen_id}.svg"
        self._accent = "#22D3EE"
        self._accent_soft_dark = "rgba(6, 182, 212, 0.14)"
        self._accent_soft_light = "rgba(34, 211, 238, 0.20)"
        self._is_light_theme = False

        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(52)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setLayoutDirection(Qt.LeftToRight)

        self._icon = QLabel("", self)
        self._icon.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self._icon.setObjectName("NavIconBadge")
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setFixedSize(
            SIDEBAR_ICON_BADGE_SIZE,
            SIDEBAR_ICON_BADGE_SIZE,
        )

        self._icon_glyph = QLabel("", self._icon)
        self._icon_glyph.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self._icon_glyph.setObjectName("NavIcon")
        self._icon_glyph.setAlignment(Qt.AlignCenter)
        self._icon_glyph.setGeometry(
            0,
            0,
            SIDEBAR_ICON_BADGE_SIZE,
            SIDEBAR_ICON_BADGE_SIZE,
        )

        self._arrow = QLabel("›", self)
        self._arrow.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self._arrow.setObjectName("NavArrow")
        self._arrow.setAlignment(Qt.AlignCenter)
        self._arrow.setFixedSize(14, 30)
        self._arrow.hide()

        self.setStyleSheet(
            "QPushButton#NavButton {"
            " text-align: left;"
            f" padding-left: {SIDEBAR_TEXT_LEFT_PADDING}px;"
            " padding-right: 28px;"
            "}"
        )
        self._sync_icon_state(False)

    def set_accent(
        self,
        accent: str,
        accent_soft_dark: str,
        accent_soft_light: str,
    ) -> None:
        self._accent = accent
        self._accent_soft_dark = accent_soft_dark
        self._accent_soft_light = accent_soft_light
        self._sync_icon_state(self.isChecked())

    def set_theme_mode(self, is_light: bool) -> None:
        self._is_light_theme = is_light
        self._sync_icon_state(self.isChecked())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        badge_y = max(10, (self.height() - self._icon.height()) // 2)
        self._icon.move(SIDEBAR_ICON_BADGE_LEFT, badge_y)

        self._arrow.move(self.width() - 26, badge_y)
        self._arrow.raise_()

    def setChecked(self, checked: bool) -> None:  # type: ignore[override]
        super().setChecked(checked)
        self._arrow.setVisible(checked)
        self._sync_icon_state(checked)

    def _sync_icon_state(self, active: bool) -> None:
        if active:
            bg = (
                self._accent_soft_light
                if self._is_light_theme
                else self._accent_soft_dark
            )
            fg = self._accent
            border = self._accent
            weight = "800"
        else:
            if self._is_light_theme:
                bg = "rgba(15, 23, 42, 0.04)"
                fg = "#64748B"
                border = "rgba(15, 23, 42, 0.10)"
            else:
                bg = "rgba(255, 255, 255, 0.02)"
                fg = "#90A4C6"
                border = "rgba(255, 255, 255, 0.08)"
            weight = "700"

        self._icon.setStyleSheet(
            f"background-color: {bg};"
            f"border: 1px solid {border};"
            "border-radius: 10px;"
        )
        self._icon.setText("")

        self._icon_glyph.setStyleSheet(
            "background-color: transparent;"
            "padding: 0px;"
            "margin: 0px;"
            "border: none;"
            f"color: {fg};"
            f"font-weight: {weight}; font-size: 13px;"
        )

        pixmap = _render_svg_icon(
            self._icon_path,
            fg,
            SIDEBAR_ICON_BADGE_SIZE,
            SIDEBAR_ICON_RENDER_SIZE,
        )
        if pixmap.isNull():
            self._icon.setText("")
            self._icon_glyph.setPixmap(QPixmap())
            self._icon_glyph.setText(self._fallback_icon_text)
        else:
            self._icon.setText("")
            self._icon_glyph.setText("")
            self._icon_glyph.setPixmap(pixmap)


class Sidebar(QFrame):
    screen_selected = Signal(str)

    def __init__(
        self,
        style_vm: StyleViewModel,
        on_apply_theme: Callable[[str, str], None],
        active_workflows: list[str],
    ) -> None:
        super().__init__()
        self.setObjectName("SidebarCard")
        self.setFixedWidth(320)
        self.setMinimumWidth(320)
        self.setMaximumWidth(320)
        self._style_vm = style_vm
        self._on_apply_theme = on_apply_theme
        self._prefs = self._style_vm.load()
        self._buttons: dict[str, NavButton] = {}
        self._current_accent = self._prefs.get("accent_palette") or "cyan"
        self._window_menu: QMenu | None = None
        self._brand_badge: QLabel | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        brand = QFrame()
        brand.setObjectName("PanelCardSoft")
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(14, 14, 14, 14)
        brand_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        badge = QLabel("")
        badge.setObjectName("BrandBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(44, 44)
        accent_palette = ACCENTS.get(
            self._current_accent,
            ACCENTS["cyan"],
        )
        brand_icon = _render_svg_icon(
            _icons_root() / "brand" / "main.svg",
            accent_palette["accent"],
            44,
            33,
        )
        if not brand_icon.isNull():
            badge.setPixmap(brand_icon)
        self._brand_badge = badge

        title = QLabel(self._text("app.name"))
        title.setObjectName("SidebarTitle")
        title.setToolTip(self._text("app.name"))
        title.setWordWrap(False)
        title.setMinimumWidth(0)

        top_row.addWidget(badge, 0, Qt.AlignTop)
        top_row.addWidget(title, 1, Qt.AlignVCenter)
        brand_layout.addLayout(top_row)

        self._window_toggle = QPushButton(
            self._text("shell.panels.decorated")
        )
        self._window_toggle.setObjectName("SidebarMenuButton")
        self._window_toggle.setMinimumHeight(32)
        self._window_toggle.setMaximumHeight(32)
        self._window_toggle.setMaximumWidth(600)
        self._window_toggle.setCursor(Qt.PointingHandCursor)
        self._window_toggle.clicked.connect(self._show_window_menu)
        brand_layout.addWidget(self._window_toggle, 0, Qt.AlignHCenter)
        root.addWidget(brand)

        self._theme_block = QFrame()
        self._theme_block.setObjectName("PanelCardSoft")
        theme_layout = QVBoxLayout(self._theme_block)
        theme_layout.setContentsMargins(14, 14, 14, 14)
        theme_layout.setSpacing(10)

        theme_header = QHBoxLayout()
        self._theme_title = QLabel(self._text("shell.themes"))
        self._theme_title.setObjectName("CardTitle")
        self._theme_toggle = QToolButton()
        self._theme_toggle.setObjectName("ThemeToggle")
        self._theme_toggle.setCheckable(True)
        self._theme_toggle.setChecked(False)
        self._theme_toggle.setText(self._text("shell.show"))
        self._theme_toggle.clicked.connect(self._toggle_theme_panel)
        theme_header.addWidget(self._theme_title)
        theme_header.addStretch(1)
        theme_header.addWidget(self._theme_toggle)
        theme_layout.addLayout(theme_header)

        self._theme_buttons_wrap = QWidget()
        self._theme_buttons_wrap.setProperty("transparentBg", True)
        theme_buttons_layout = QHBoxLayout(self._theme_buttons_wrap)
        theme_buttons_layout.setContentsMargins(0, 0, 0, 0)
        theme_buttons_layout.setSpacing(8)
        for key, meta in THEMES.items():
            button = QPushButton(meta["label"])
            button.setObjectName("ThemeChip")
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(34)
            button.clicked.connect(
                lambda _checked=False, theme_key=key: self._apply_theme(
                    theme_key
                )
            )
            theme_buttons_layout.addWidget(button)
        theme_layout.addWidget(self._theme_buttons_wrap)
        self._theme_buttons_wrap.hide()

        scale_header = QHBoxLayout()
        self._scale_title = QLabel(self._text("shell.scale"))
        self._scale_title.setObjectName("CardTitle")
        self._scale_value = QLabel("")
        self._scale_value.setObjectName("TelemetryChip")
        self._scale_toggle = QToolButton()
        self._scale_toggle.setObjectName("ThemeToggle")
        self._scale_toggle.setCheckable(True)
        self._scale_toggle.setChecked(False)
        self._scale_toggle.setText(self._text("shell.show"))
        self._scale_toggle.clicked.connect(self._toggle_scale_panel)
        scale_header.addWidget(self._scale_title)
        scale_header.addStretch(1)
        scale_header.addWidget(self._scale_value)
        scale_header.addWidget(self._scale_toggle)
        theme_layout.addLayout(scale_header)

        self._scale_wrap = QWidget()
        self._scale_wrap.setProperty("transparentBg", True)
        scale_layout = QVBoxLayout(self._scale_wrap)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.setSpacing(8)

        self._scale_slider = QSlider(Qt.Horizontal)
        self._scale_slider.setRange(
            int(MIN_UI_SCALE * 100),
            int(MAX_UI_SCALE * 100),
        )
        self._scale_slider.setSingleStep(1)
        self._scale_slider.setPageStep(4)
        self._scale_slider.setCursor(Qt.PointingHandCursor)
        self._scale_slider.valueChanged.connect(self._apply_scale_live)
        self._scale_slider.sliderReleased.connect(
            self._save_scale_from_slider
        )
        scale_layout.addWidget(self._scale_slider)

        scale_actions = QHBoxLayout()
        self._scale_hint = QLabel("")
        self._scale_hint.setObjectName("MutedText")
        self._reset_scale = QPushButton(
            self._text("shell.scale.auto_button")
        )
        self._reset_scale.setObjectName("SidebarMenuButton")
        self._reset_scale.setCursor(Qt.PointingHandCursor)
        self._reset_scale.clicked.connect(self._reset_scale_auto)
        scale_actions.addWidget(self._scale_hint, 1)
        scale_actions.addWidget(self._reset_scale)
        scale_layout.addLayout(scale_actions)

        theme_layout.addWidget(self._scale_wrap)
        self._scale_wrap.hide()
        self._sync_scale_controls()

        root.addWidget(self._theme_block)

        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("StableScrollArea")
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        apply_scrollbar_style(nav_scroll)

        nav_container = QFrame()
        nav_container.setObjectName("SidebarNav")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(8)

        items = [
            ("dashboard", "П", "nav.dashboard"),
            ("profiles", "ПР", "nav.profiles"),
            ("agents", "АГ", "nav.agents"),
            ("datasets", "ДС", "nav.datasets"),
            ("training", "ОБ", "nav.training"),
            ("snapshots", "СН", "nav.snapshots"),
            ("tests", "ТС", "nav.tests"),
            ("analysis", "АН", "nav.analysis"),
            ("style", "ОФ", "nav.style"),
            ("docs", "ДК", "nav.docs"),
        ]
        for screen_id, icon_text, title_key in items:
            button = NavButton(
                screen_id,
                icon_text,
                self._text(title_key),
            )
            accent_palette = ACCENTS.get(
                self._current_accent,
                ACCENTS["cyan"],
            )
            button.set_accent(
                accent_palette["accent"],
                accent_palette["accent_soft_dark"],
                accent_palette["accent_soft_light"],
            )
            button.clicked.connect(
                lambda checked=False, sid=screen_id: self._select_screen(sid)
            )
            nav_layout.addWidget(button)
            self._buttons[screen_id] = button
        nav_layout.addStretch(1)
        nav_scroll.setWidget(nav_container)
        root.addWidget(nav_scroll, 1)

        workflows = QFrame()
        workflows.setObjectName("PanelCardSoft")
        wf_layout = QVBoxLayout(workflows)
        wf_layout.setContentsMargins(14, 14, 14, 14)
        wf_layout.setSpacing(10)
        self._workflow_title = QLabel(
            self._text("shell.active_processes")
        )
        self._workflow_title.setObjectName("SidebarWorkflowsTitle")
        wf_layout.addWidget(self._workflow_title)
        for item in active_workflows:
            pill = QLabel(item)
            pill.setObjectName("WorkflowPill")
            wf_layout.addWidget(pill)
        root.addWidget(workflows, 0)

        self._sync_accent_from_app()
        self.set_current("dashboard")

    def _text(self, key: str, **values: object) -> str:
        return base_text(key, **values)

    def set_window_menu(self, menu: QMenu) -> None:
        self._window_menu = menu

    def _show_window_menu(self) -> None:
        if self._window_menu is None:
            return
        self._window_menu.exec(QCursor.pos())

    def _toggle_theme_panel(self, checked: bool) -> None:
        self._theme_buttons_wrap.setVisible(checked)
        if checked:
            self._theme_toggle.setText(self._text("shell.hide"))
        else:
            self._theme_toggle.setText(self._text("shell.show"))

    def _toggle_scale_panel(self, checked: bool) -> None:
        self._scale_wrap.setVisible(checked)
        if checked:
            self._scale_toggle.setText(self._text("shell.hide"))
        else:
            self._scale_toggle.setText(self._text("shell.show"))

    def _sync_scale_controls(self) -> None:
        app = QApplication.instance()
        auto_scale = current_scale()
        if app is not None:
            try:
                auto_scale = float(
                    app.property("ptl_ui_auto_scale") or auto_scale
                )
            except (TypeError, ValueError):
                pass
        saved = self._prefs.get("ui_scale") or "auto"
        if saved == "auto":
            value = int(round(auto_scale * 100))
            label = self._text("shell.scale.auto_value", value=value)
            hint = self._text("shell.scale.auto_hint")
        else:
            try:
                value = int(round(float(saved) * 100))
            except ValueError:
                value = int(round(auto_scale * 100))
            label = f"{value}%"
            hint = self._text("shell.scale.applies_immediately")
        self._scale_slider.blockSignals(True)
        self._scale_slider.setValue(value)
        self._scale_slider.blockSignals(False)
        self._scale_value.setText(label)
        self._scale_hint.setText(hint)

    def _apply_scale_live(self, value: int) -> None:
        scale = value / 100
        app = QApplication.instance()
        if app is not None:
            app.setProperty("ptl_ui_scale", scale)
            app.setProperty("ptl_ui_density", f"manual {value}%")
            app.setProperty("ptl_ui_scale_manual", True)
            apply_scaled_styles(app, scale)
            window = self.window()
            if window is not None:
                window.updateGeometry()
                window.update()
        self._scale_value.setText(f"{value}%")
        self._scale_hint.setText(
            self._text("shell.scale.applies_immediately")
        )

    def _save_scale_from_slider(self) -> None:
        value = self._scale_slider.value()
        scale = value / 100
        app = QApplication.instance()
        if app is not None:
            apply_scaled_styles(app, scale, immediate=True)
        self._style_vm.save_ui_scale(f"{scale:.2f}")
        self._prefs = self._style_vm.load()
        self._scale_value.setText(f"{value}%")
        self._scale_hint.setText(self._text("shell.scale.saved"))

    def _reset_scale_auto(self) -> None:
        app = QApplication.instance()
        auto_scale = current_scale()
        if app is not None:
            try:
                auto_scale = float(
                    app.property("ptl_ui_auto_scale") or auto_scale
                )
            except (TypeError, ValueError):
                pass
            app.setProperty("ptl_ui_scale", auto_scale)
            app.setProperty("ptl_ui_density", "auto")
            app.setProperty("ptl_ui_scale_manual", False)
            apply_scaled_styles(app, auto_scale, immediate=True)
            window = self.window()
            if window is not None:
                window.updateGeometry()
                window.update()
        self._style_vm.save_ui_scale("auto")
        self._prefs = self._style_vm.load()
        self._sync_scale_controls()
        self._scale_hint.setText(
            self._text("shell.scale.auto_enabled")
        )

    def _apply_theme(self, theme_key: str) -> None:
        self._style_vm.save(
            theme=theme_key,
            accent_palette=self._current_accent,
            button_style_preset="soft_glow",
        )
        self._on_apply_theme(theme_key, self._current_accent)
        self._sync_accent_from_app()

    def _sync_accent_from_app(self) -> None:
        app = QApplication.instance()
        accent_palette = ACCENTS.get(
            self._current_accent,
            ACCENTS["cyan"],
        )
        if app is not None:
            accent_name = app.property("ptl_accent_name")
            if isinstance(accent_name, str):
                self._current_accent = accent_name
                if accent_name in ACCENTS:
                    accent_palette = ACCENTS[accent_name]
                elif accent_name.startswith("#"):
                    accent_palette = _custom_accent_palette(accent_name)
        is_light_theme = False
        app = QApplication.instance()
        if app is not None:
            theme_name = app.property("ptl_theme_name")
            if isinstance(theme_name, str):
                is_light_theme = (
                    THEMES.get(theme_name, THEMES["velvet"]).get(
                        "is_light"
                    )
                    == "1"
                )
        for button in self._buttons.values():
            button.set_accent(
                accent_palette["accent"],
                accent_palette["accent_soft_dark"],
                accent_palette["accent_soft_light"],
            )
            button.set_theme_mode(is_light_theme)
        if self._brand_badge is not None:
            icon = _render_svg_icon(
                _icons_root() / "brand" / "main.svg",
                accent_palette["accent"],
                44,
                33,
            )
            if not icon.isNull():
                self._brand_badge.setPixmap(icon)

    def _select_screen(self, screen_id: str) -> None:
        self.set_current(screen_id)
        self.screen_selected.emit(screen_id)

    def set_current(self, screen_id: str) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == screen_id)

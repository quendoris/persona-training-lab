from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, Signal, QRect, QRectF
from PySide6.QtGui import QColor, QCursor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.themes.tokens import THEMES
from persona_training_lab.ui.viewmodels.style import StyleViewModel

SIDEBAR_ICON_RENDER_SIZE = 18
SIDEBAR_ICON_OPTICAL_OFFSET_X = -6
SIDEBAR_ICON_BADGE_LEFT = 8
SIDEBAR_TEXT_LEFT_PADDING = 56


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
        shifted_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        shifted_painter.drawPixmap(shifted_x, target_y, pixmap.copy(target.toRect()))
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
    final_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    max_crop_x = max(0, canvas_size - cropped.width())
    final_x = max(0, min(round((canvas_size - cropped.width()) / 2) + offset_x, max_crop_x))
    final_y = max(0, min(round((canvas_size - cropped.height()) / 2), canvas_size - cropped.height()))
    final_painter.drawPixmap(final_x, final_y, cropped)
    final_painter.end()
    return final_pixmap


class NavButton(QPushButton):
    def __init__(self, screen_id: str, icon_text: str, title: str) -> None:
        super().__init__(title)
        self.screen_id = screen_id
        self._fallback_icon_text = icon_text
        self._icon_path = _icons_root() / "sidebar" / f"{screen_id}.svg"

        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(52)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setLayoutDirection(Qt.LeftToRight)

        self._icon = QLabel(icon_text, self)
        self._icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._icon.setObjectName("NavIcon")
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setFixedSize(30, 30)

        self._arrow = QLabel("›", self)
        self._arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._arrow.setObjectName("NavArrow")
        self._arrow.setAlignment(Qt.AlignCenter)
        self._arrow.setFixedSize(14, 30)
        self._arrow.hide()

        self.setStyleSheet(
            f"text-align: left; padding-left: {SIDEBAR_TEXT_LEFT_PADDING}px; padding-right: 28px;"
        )
        self._sync_icon_state(False)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        y = max(10, (self.height() - self._icon.height()) // 2)
        self._icon.move(SIDEBAR_ICON_BADGE_LEFT, y)
        self._arrow.move(self.width() - 26, y)
        self._icon.raise_()
        self._arrow.raise_()

    def setChecked(self, checked: bool) -> None:  # type: ignore[override]
        super().setChecked(checked)
        self._arrow.setVisible(checked)
        self._sync_icon_state(checked)

    def _sync_icon_state(self, active: bool) -> None:
        if active:
            bg = "rgba(6, 182, 212, 0.14)"
            fg = "#22D3EE"
            border = "rgba(6, 182, 212, 0.72)"
            weight = "800"
        else:
            bg = "rgba(255, 255, 255, 0.02)"
            fg = "#90A4C6"
            border = "rgba(255, 255, 255, 0.08)"
            weight = "700"

        self._icon.setStyleSheet(
            f"background-color: {bg};"
            f"color: {fg};"
            f"border: 1px solid {border};"
            "border-radius: 10px;"
            f"font-weight: {weight}; font-size: 13px;"
        )

        pixmap = _render_svg_icon(
            self._icon_path,
            fg,
            30,
            SIDEBAR_ICON_RENDER_SIZE,
            offset_x=SIDEBAR_ICON_OPTICAL_OFFSET_X,
            tight_crop=True,
        )
        if pixmap.isNull():
            self._icon.setPixmap(QPixmap())
            self._icon.setText(self._fallback_icon_text)
        else:
            self._icon.setText("")
            self._icon.setPixmap(pixmap)


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
        brand_icon = _render_svg_icon(_icons_root() / "brand" / "main.svg", "#22D3EE", 44, 33)
        if not brand_icon.isNull():
            badge.setPixmap(brand_icon)

        title = QLabel("Persona Training Lab")
        title.setObjectName("SidebarTitle")
        title.setToolTip("Persona Training Lab")
        title.setWordWrap(False)
        title.setMinimumWidth(0)

        top_row.addWidget(badge, 0, Qt.AlignTop)
        top_row.addWidget(title, 1, Qt.AlignVCenter)
        brand_layout.addLayout(top_row)

        self._window_toggle = QPushButton("┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ панели ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈")
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
        theme_title = QLabel("Темы")
        self._theme_toggle = QToolButton()
        self._theme_toggle.setObjectName("ThemeToggle")
        self._theme_toggle.setCheckable(True)
        self._theme_toggle.setChecked(False)
        self._theme_toggle.setText("показать")
        self._theme_toggle.clicked.connect(self._toggle_theme_panel)
        theme_header.addWidget(theme_title)
        theme_header.addStretch(1)
        theme_header.addWidget(self._theme_toggle)
        theme_layout.addLayout(theme_header)

        self._theme_buttons_wrap = QWidget()
        theme_buttons_layout = QHBoxLayout(self._theme_buttons_wrap)
        theme_buttons_layout.setContentsMargins(0, 0, 0, 0)
        theme_buttons_layout.setSpacing(8)
        for key, meta in THEMES.items():
            button = QPushButton(meta["label"])
            button.setObjectName("ThemeChip")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, theme_key=key: self._apply_theme(theme_key))
            theme_buttons_layout.addWidget(button)
        theme_layout.addWidget(self._theme_buttons_wrap)
        self._theme_buttons_wrap.hide()
        root.addWidget(self._theme_block)

        nav_scroll = QScrollArea()
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        nav_container = QFrame()
        nav_container.setObjectName("SidebarNav")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(8)

        items = [
            ("dashboard", "П", "Панель"),
            ("profiles", "ПР", "Профили"),
            ("datasets", "ДС", "Датасеты"),
            ("training", "ОБ", "Обучение"),
            ("snapshots", "СН", "Снимки"),
            ("tests", "ТС", "Тесты"),
            ("analysis", "АН", "Анализ"),
            ("style", "ОФ", "Оформление"),
            ("docs", "ДК", "Документация"),
        ]
        for screen_id, icon_text, title_text in items:
            button = NavButton(screen_id, icon_text, title_text)
            button.clicked.connect(lambda checked=False, sid=screen_id: self._select_screen(sid))
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
        wf_title = QLabel("Активные процессы")
        wf_title.setObjectName("SectionTitle")
        wf_layout.addWidget(wf_title)
        for item in active_workflows:
            pill = QLabel(item)
            pill.setObjectName("WorkflowPill")
            wf_layout.addWidget(pill)
        root.addWidget(workflows, 0)

        self.set_current("dashboard")

    def set_window_menu(self, menu: QMenu) -> None:
        self._window_menu = menu

    def _show_window_menu(self) -> None:
        if self._window_menu is None:
            return
        self._window_menu.exec(QCursor.pos())

    def _toggle_theme_panel(self, checked: bool) -> None:
        self._theme_buttons_wrap.setVisible(checked)
        self._theme_toggle.setText("скрыть" if checked else "показать")

    def _apply_theme(self, theme_key: str) -> None:
        self._style_vm.save(theme=theme_key, accent_palette=self._current_accent, button_style_preset="soft_glow")
        self._on_apply_theme(theme_key, self._current_accent)

    def _select_screen(self, screen_id: str) -> None:
        self.set_current(screen_id)
        self.screen_selected.emit(screen_id)

    def set_current(self, screen_id: str) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == screen_id)

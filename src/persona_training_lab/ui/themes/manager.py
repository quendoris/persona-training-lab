from __future__ import annotations

from string import Template

from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.themes.tokens import ACCENTS, DEFAULT_ACCENT, DEFAULT_THEME, THEMES


def _resolve(theme_name: str | None, accent_name: str | None) -> tuple[dict[str, str], dict[str, str]]:
    theme = THEMES.get(theme_name or DEFAULT_THEME, THEMES[DEFAULT_THEME]).copy()
    accent = ACCENTS.get(accent_name or DEFAULT_ACCENT, ACCENTS[DEFAULT_ACCENT]).copy()
    if theme.get("is_light") == "1":
        accent["accent_soft"] = accent["accent_soft_light"]
        accent["accent_text"] = accent["accent_text_light"]
    else:
        accent["accent_soft"] = accent["accent_soft_dark"]
        accent["accent_text"] = accent["accent_text_dark"]
    return theme, accent


def build_stylesheet(theme_name: str | None = None, accent_name: str | None = None) -> str:
    theme, accent = _resolve(theme_name, accent_name)
    values = {
        "window_bg": theme["window_bg"],
        "surface_bg": theme["surface_bg"],
        "surface_alt": theme["surface_alt"],
        "surface_soft": theme["surface_soft"],
        "border": theme["border"],
        "border_soft": theme["border_soft"],
        "selection_bg": theme["selection_bg"],
        "text_primary": theme["text_primary"],
        "text_secondary": theme["text_secondary"],
        "text_muted": theme["text_muted"],
        "titlebar": theme["titlebar"],
        "accent": accent["accent"],
        "accent_soft": accent["accent_soft"],
        "accent_text": accent["accent_text"],
        "accent_hover": accent["accent_hover"],
        "accent_pressed": accent["accent_pressed"],
    }
    template = Template("""
    QWidget {
        background-color: $window_bg;
        color: $text_primary;
        font-size: 13px;
        selection-background-color: $selection_bg;
        selection-color: $text_primary;
    }
    QLabel {
        background: transparent;
    }
    QMainWindow, QDockWidget, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {
        background-color: $window_bg;
    }
    QFrame#ShellHeader {
        background-color: $surface_bg;
        border: 1px solid $border;
        border-radius: 24px;
    }
    QFrame#PanelCard {
        background-color: $surface_bg;
        border: 1px solid $border;
        border-radius: 22px;
    }
    QFrame#PanelCardSoft {
        background-color: $surface_alt;
        border: 1px solid $border_soft;
        border-radius: 18px;
    }
    QFrame#AccentCard {
        background-color: $accent_soft;
        border: 1px solid $accent;
        border-radius: 22px;
    }
    QFrame#SidebarCard {
        background-color: $surface_bg;
        border: 1px solid $border;
        border-radius: 28px;
    }
    QFrame#SidebarNav {
        background-color: $surface_soft;
        border: 1px solid $border_soft;
        border-radius: 22px;
    }
    QLabel#ScreenTitle {
        background: transparent;
        font-size: 28px;
        font-weight: 800;
    }
    QLabel#SectionTitle {
        background: transparent;
        font-size: 17px;
        font-weight: 700;
    }
    QLabel#SidebarTitle {
        background: transparent;
        font-size: 16px;
        font-weight: 800;
    }
    QLabel#CardTitle {
        background: transparent;
        font-size: 14px;
        font-weight: 700;
    }
    QLabel#MetricValue {
        background: transparent;
        font-size: 30px;
        font-weight: 800;
    }
    QLabel#MutedText {
        background: transparent;
        color: $text_muted;
    }
    QLabel#StatusSuccess {
        color: $accent_text;
        background: $accent_soft;
        border: 1px solid $accent;
        padding: 4px 10px;
        border-radius: 999px;
        font-weight: 700;
    }
    QLabel#StatusWarning {
        color: #fcd34d;
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.35);
        padding: 4px 10px;
        border-radius: 999px;
        font-weight: 700;
    }
    QLabel#BrandBadge, QLabel#ActionIcon, QLabel#LineageIcon {
        background-color: $accent_soft;
        color: $accent_text;
        border: 1px solid $accent;
        border-radius: 12px;
        font-weight: 800;
    }
    QLabel#NavIcon {
        background-color: $surface_alt;
        color: $text_secondary;
        border: 1px solid $border_soft;
        border-radius: 10px;
        font-weight: 800;
        font-size: 14px;
    }
    QLabel#NavArrow {
        color: $accent_text;
        font-size: 16px;
        font-weight: 800;
    }
    QPushButton#NavButton {
        background-color: $surface_alt;
        color: $text_secondary;
        border: 1px solid $border_soft;
        border-radius: 18px;
        font-weight: 700;
        min-height: 46px;
    }
    QPushButton#NavButton:hover {
        background-color: $selection_bg;
        border: 1px solid $accent;
    }
    QPushButton#NavButton:checked {
        background-color: $selection_bg;
        color: $text_primary;
        border: 1px solid $accent;
    }
    QPushButton#ThemeChip {
        background-color: $surface_alt;
        color: $text_primary;
        border: 1px solid $border;
        border-radius: 999px;
        padding: 8px 12px;
        font-weight: 600;
    }
    QPushButton#ThemeChip:hover {
        background-color: $selection_bg;
    }
    QToolButton#ThemeToggle, QToolButton#WindowToggle {
        background: transparent;
        color: $text_secondary;
        border: none;
        font-weight: 700;
        padding: 4px 8px;
    }
    QToolButton#WindowToggle::menu-indicator {
        image: none;
        width: 0px;
    }

    QPushButton#SidebarMenuButton {
        background-color: $selection_bg;
        color: $text_primary;
        border: 1px solid $accent;
        border-radius: 12px;
        padding: 4px 14px;
        font-weight: 800;
        min-height: 20px;
    }
    QPushButton#SidebarMenuButton:hover {
        border: 1px solid $accent;
        background-color: $surface_soft;
    }
    QListWidget#DocsTopicList {
    background: transparent;
    border: none;
    outline: none;
    padding: 2px;
    }

    QListWidget#DocsTopicList::item {
        background-color: transparent;
        color: $text_primary;
        border: 1px solid $border_soft;
        border-radius: 12px;
        padding: 10px 12px;
        margin: 2px 0;
    }

    QListWidget#DocsTopicList::item:hover {
        background-color: $surface_soft;
        border: 1px solid $accent;
    }

    QListWidget#DocsTopicList::item:selected {
        background-color: $selection_bg;
        border: 1px solid $accent;
        color: $text_primary;
    }
    QWidget[transparentBg="true"] {
        background: transparent;
        border: none;
    }
    QWidget#TelemetryMetricsHost,
    QWidget#TelemetryMetricsViewport,
    QWidget#TelemetryProcessesContainer,
    QWidget#TelemetryProcessesViewport,
    QScrollArea#TelemetryProcessesScroll,
    QScrollArea#TelemetryProcessesScroll > QWidget > QWidget {
        background: transparent;
        border: none;
    }
    QLabel#WorkflowPill {
        background-color: $surface_alt;
        border: 1px solid $border;
        border-radius: 14px;
        padding: 10px 12px;
        color: $text_primary;
    }
    QFrame#ActionCard {
        background-color: $surface_alt;
        border: 1px solid $border_soft;
        border-radius: 20px;
    }
    QFrame#WarningBlock {
        background-color: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.22);
        border-radius: 18px;
    }
    QFrame#StableScrollWrap {
        background-color: $surface_soft;
        border: 1px solid $border_soft;
        border-radius: 18px;
    }
    QFrame#StableScrollShell,
    QFrame#CheckpointScrollShell {
        background-color: $surface_soft;
        border: 1px solid $border_soft;
        border-radius: 18px;
    }
    QFrame#LineageRow {
        background-color: $surface_alt;
        border: 1px solid $border_soft;
        border-radius: 16px;
    }
    QScrollBar:vertical {
        background-color: $surface_soft;
        width: 14px;
        margin: 2px 2px 2px 0px;
        border: 1px solid $border_soft;
        border-radius: 7px;
    }
    QScrollBar:horizontal {
        background-color: $surface_soft;
        height: 14px;
        margin: 0px 2px 2px 2px;
        border: 1px solid $border_soft;
        border-radius: 7px;
    }
    QScrollBar::handle:vertical {
        background-color: $accent;
        border: 1px solid $accent_hover;
        border-radius: 999px;
        min-height: 34px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal {
        background-color: $accent;
        border: 1px solid $accent_hover;
        border-radius: 999px;
        min-width: 34px;
        margin: 2px;
    }
    QScrollBar:vertical::handle:vertical,
    QScrollBar:horizontal::handle:horizontal {
        border-radius: 999px;
    }
    QScrollBar::handle:vertical:hover,
    QScrollBar::handle:horizontal:hover {
        background-color: $accent_hover;
        border: 1px solid $accent;
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal,
    QScrollBar::up-arrow,
    QScrollBar::down-arrow,
    QScrollBar::left-arrow,
    QScrollBar::right-arrow {
        background: transparent;
        border: none;
        width: 0px;
        height: 0px;
    }
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical,
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {
        background: transparent;
        border: none;
    }
    QListWidget, QTextEdit, QPlainTextEdit, QComboBox, QLineEdit {
        background-color: $surface_alt;
        color: $text_primary;
        border: 1px solid $border;
        border-radius: 16px;
        padding: 8px;
    }
    QComboBox {
        padding-right: 30px;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 26px;
        border: none;
        background: transparent;
        border-top-right-radius: 16px;
        border-bottom-right-radius: 16px;
    }
    QComboBox::down-arrow {
        image: url(src/persona_training_lab/ui/assets/icons/chevron_down.svg);
        width: 10px;
        height: 6px;
        margin-right: 10px;
        background: transparent;
    }
    QComboBox::down-arrow:on,
    QComboBox::down-arrow:hover {
        image: url(src/persona_training_lab/ui/assets/icons/chevron_down.svg);
    }
    QTableWidget {
        background-color: $surface_alt;
        color: $text_primary;
        gridline-color: $border_soft;
        border: 1px solid $border;
        border-radius: 16px;
    }
    QHeaderView::section {
        background-color: $surface_soft;
        color: $text_secondary;
        border: none;
        border-bottom: 1px solid $border_soft;
        padding: 8px 10px;
        font-weight: 700;
    }
    QTableCornerButton::section {
        background-color: $surface_soft;
        border: none;
        border-bottom: 1px solid $border_soft;
    }
    QListWidget::item {
        padding: 10px 12px;
        margin: 2px 0;
        border-radius: 12px;
        background: transparent;
    }
    QListWidget::item:selected {
        background-color: $selection_bg;
        border: 1px solid $accent;
    }
    QListWidget::item:hover {
        background-color: $surface_soft;
    }
    QPushButton#SecondaryButton {
        background-color: $surface_alt;
        color: $text_primary;
        border: 1px solid $border;
        border-radius: 16px;
        padding: 12px 16px;
        font-weight: 800;
    }
    QPushButton#SecondaryButton:hover {
        background-color: $selection_bg;
    }
    QPushButton {
        background-color: $accent;
        color: white;
        border: none;
        border-radius: 16px;
        padding: 12px 16px;
        font-weight: 800;
    }
    QPushButton:hover {
        background-color: $accent_hover;
    }
    QPushButton:pressed {
        background-color: $accent_pressed;
    }
    QMenu {
        background-color: $surface_bg;
        color: $text_primary;
        border: 1px solid $border;
        border-radius: 14px;
        padding: 6px;
    }
    QMenu::item {
        padding: 8px 18px;
        border-radius: 10px;
        margin: 2px 0;
    }
    QMenu::item:selected {
        background: $selection_bg;
    }
    QDockWidget::title {
        background: $titlebar;
        padding: 8px 10px;
        border-bottom: 1px solid $border;
        font-weight: 700;
    }
    QStatusBar {
        background: $surface_bg;
        color: $text_secondary;
        border-top: 1px solid $border;
    }
    QLabel#TelemetryCaption {
        color: $text_muted;
        font-size: 11px;
        background: transparent;
    }
    QLabel#TelemetryChip {
        color: $text_secondary;
        background-color: $surface_alt;
        border: 1px solid $border_soft;
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 11px;
        font-weight: 700;
    }
    QLabel#MetricPercentPill {
        color: $text_primary;
        background-color: $surface_alt;
        border: 1px solid $border_soft;
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 11px;
        font-weight: 800;
        min-width: 44px;
    }
    QFrame#TelemetryBarTrack {
        background-color: $surface_soft;
        border: 1px solid $border_soft;
        border-radius: 12px;
    }
    QFrame#TelemetryBarFill {
        background-color: $accent;
        border-radius: 10px;
    }
    QToolTip {
        background-color: $surface_bg;
        color: $text_primary;
        border: 1px solid $border;
        padding: 8px 10px;
    }
    """)
    return template.substitute(values)


def apply_theme(app: QApplication, theme_name: str | None = None, accent_name: str | None = None) -> None:
    app.setStyleSheet(build_stylesheet(theme_name, accent_name))

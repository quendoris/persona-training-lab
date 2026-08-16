from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.themes.tokens import ACCENTS, THEMES
from persona_training_lab.ui.viewmodels.style import StyleViewModel


class StyleScreen(QWidget):
    def __init__(
        self,
        view_model: StyleViewModel,
        on_apply: Callable[[str, str], None],
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._on_apply = on_apply
        self._localization = localization

        prefs = self._vm.load()
        current_theme = prefs.get("theme") or "velvet"
        current_accent = prefs.get("accent_palette") or "cyan"

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        self._controls = PanelCard("", "")

        self._language_label = QLabel()
        self._controls.add_widget(self._language_label)
        self._language_box = QComboBox()
        if localization is not None:
            for locale in localization.available_locales():
                self._language_box.addItem(
                    localization.locale_name(locale),
                    locale,
                )
            language_index = self._language_box.findData(localization.locale)
            if language_index >= 0:
                self._language_box.setCurrentIndex(language_index)
            self._language_box.currentIndexChanged.connect(self._change_language)
        else:
            self._language_box.setEnabled(False)
        self._controls.add_widget(self._language_box)
        self._language_note = make_muted_label("")
        self._controls.add_widget(self._language_note)

        self._theme_label = QLabel()
        self._controls.add_widget(self._theme_label)
        self._theme_box = QComboBox()
        for key in THEMES:
            self._theme_box.addItem("", key)
        self._theme_box.setCurrentIndex(
            max(0, self._theme_box.findData(current_theme))
        )
        self._controls.add_widget(self._theme_box)

        self._accent_label = QLabel()
        self._controls.add_widget(self._accent_label)
        self._accent_box = QComboBox()
        for key in ACCENTS:
            self._accent_box.addItem("", key)
        accent_key = current_accent if current_accent in ACCENTS else "cyan"
        self._accent_box.setCurrentIndex(
            max(0, self._accent_box.findData(accent_key))
        )
        self._controls.add_widget(self._accent_box)

        accent_custom_row = QWidget()
        accent_custom_row.setProperty("transparentBg", True)
        accent_custom_layout = QHBoxLayout(accent_custom_row)
        accent_custom_layout.setContentsMargins(0, 0, 0, 0)
        accent_custom_layout.setSpacing(8)
        self._custom_accent_input = QLineEdit(
            current_accent
            if isinstance(current_accent, str)
            and current_accent.startswith("#")
            else ""
        )
        self._custom_accent_input.setPlaceholderText("#RRGGBB")
        self._choose_custom = QPushButton()
        self._choose_custom.setObjectName("SecondaryButton")
        self._choose_custom.clicked.connect(self._pick_custom_accent)
        accent_custom_layout.addWidget(self._custom_accent_input, 1)
        accent_custom_layout.addWidget(self._choose_custom, 0)
        self._controls.add_widget(accent_custom_row)

        self._apply_button = QPushButton()
        self._apply_button.clicked.connect(self._apply)
        self._controls.add_widget(self._apply_button)
        self._controls_note = make_muted_label("")
        self._controls.add_widget(self._controls_note)
        self._controls.add_stretch(1)
        root.addWidget(self._controls, 1)

        self._preview = PanelCard("", "")
        self._brand_label = QLabel()
        self._preview.add_widget(self._brand_label)
        self._brand_note = make_muted_label("")
        self._preview.add_widget(self._brand_note)

        row = QWidget()
        row.setProperty("transparentBg", True)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        self._primary = QPushButton()
        self._secondary = QPushButton()
        self._secondary.setObjectName("SecondaryButton")
        row_layout.addWidget(self._primary)
        row_layout.addWidget(self._secondary)
        self._preview.add_widget(row)

        badges = QWidget()
        badges.setProperty("transparentBg", True)
        badges_layout = QHBoxLayout(badges)
        badges_layout.setContentsMargins(0, 0, 0, 0)
        badges_layout.setSpacing(8)
        self._running_badge = make_status_label("")
        self._attention_badge = make_status_label("", tone="pending")
        badges_layout.addWidget(self._running_badge)
        badges_layout.addWidget(self._attention_badge)
        badges_layout.addStretch(1)
        self._preview.add_widget(badges)
        self._preview.add_stretch(1)
        root.addWidget(self._preview, 2)

        self._apply_language()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        self._controls.set_title(self._text("style.controls.title"))
        self._controls.set_subtitle(self._text("style.controls.subtitle"))
        self._language_label.setText(self._text("language.current"))
        self._language_note.setText(self._text("language.restart_not_required"))
        if self._localization is not None:
            self._language_box.blockSignals(True)
            for index in range(self._language_box.count()):
                locale = str(self._language_box.itemData(index))
                self._language_box.setItemText(
                    index,
                    self._localization.locale_name(locale),
                )
            current_index = self._language_box.findData(self._localization.locale)
            if current_index >= 0:
                self._language_box.setCurrentIndex(current_index)
            self._language_box.blockSignals(False)

        self._theme_label.setText(self._text("style.theme.label"))
        self._accent_label.setText(self._text("style.accent.label"))
        self._choose_custom.setText(self._text("style.custom_accent.choose"))
        self._apply_button.setText(self._text("style.apply"))
        self._controls_note.setText(self._text("style.controls.note"))

        for index in range(self._theme_box.count()):
            key = str(self._theme_box.itemData(index))
            self._theme_box.setItemText(index, self._text(f"style.theme.{key}"))
        for index in range(self._accent_box.count()):
            key = str(self._accent_box.itemData(index))
            self._accent_box.setItemText(index, self._text(f"style.accent.{key}"))

        self._preview.set_title(self._text("style.preview.title"))
        self._preview.set_subtitle(self._text("style.preview.subtitle"))
        self._brand_label.setText(self._text("app.name"))
        self._brand_note.setText(self._text("style.preview.brand_note"))
        self._primary.setText(self._text("style.preview.action.training"))
        self._secondary.setText(self._text("style.preview.action.compare"))
        self._running_badge.setText(self._text("style.preview.status.running"))
        self._attention_badge.setText(
            self._text("style.preview.status.attention")
        )

    def _change_language(self, _index: int) -> None:
        localization = self._localization
        if localization is None:
            return
        locale = self._language_box.currentData()
        if not isinstance(locale, str) or locale == localization.locale:
            return
        localization.set_locale(locale)

    def _apply(self) -> None:
        theme = self._theme_box.currentData()
        custom_accent = self._custom_accent_input.text().strip()
        accent = (
            custom_accent
            if custom_accent.startswith("#")
            else self._accent_box.currentData()
        )
        self._vm.save(
            theme=theme,
            accent_palette=accent,
            button_style_preset="soft_glow",
        )
        self._on_apply(theme, accent)

    def _pick_custom_accent(self) -> None:
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self._custom_accent_input.setText(color.name())

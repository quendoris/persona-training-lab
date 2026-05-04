from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.themes.tokens import ACCENTS, THEMES
from persona_training_lab.ui.viewmodels.style import StyleViewModel


class StyleScreen(QWidget):
    def __init__(
        self,
        view_model: StyleViewModel,
        on_apply: Callable[[str, str], None],
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._on_apply = on_apply

        prefs = self._vm.load()
        current_theme = prefs.get("theme") or "velvet"
        current_accent = prefs.get("accent_palette") or "cyan"

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        controls = PanelCard("Оформление", "Отдельная вкладка стиля — не декоративная мелочь, а часть комфорта при долгой работе.")
        controls.add_widget(QLabel("Тема"))
        self._theme_box = QComboBox()
        for key, meta in THEMES.items():
            self._theme_box.addItem(meta["label"], key)
        self._theme_box.setCurrentIndex(max(0, self._theme_box.findData(current_theme)))
        controls.add_widget(self._theme_box)

        controls.add_widget(QLabel("Акцент"))
        self._accent_box = QComboBox()
        for key, meta in ACCENTS.items():
            self._accent_box.addItem(meta["label"], key)
        self._accent_box.setCurrentIndex(max(0, self._accent_box.findData(current_accent)))
        controls.add_widget(self._accent_box)

        apply_button = QPushButton("Применить оформление")
        apply_button.clicked.connect(self._apply)
        controls.add_widget(apply_button)
        controls.add_widget(make_muted_label("Выбор сохраняется в SQLite и становится частью живого комфорта системы."))
        controls.add_stretch(1)
        root.addWidget(controls, 1)

        preview = PanelCard("Предпросмотр", "Стиль должен ощущаться живым и читабельным, а не абстрактным.", accented=True)
        preview.add_widget(QLabel("Persona Training Lab"))
        preview.add_widget(make_muted_label("Спокойная исследовательская рабочая станция для обучения личности и анализа версий."))

        row = QWidget()
        row.setProperty("transparentBg", True)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        primary = QPushButton("Запустить обучение")
        secondary = QPushButton("Открыть compare")
        secondary.setObjectName("SecondaryButton")
        row_layout.addWidget(primary)
        row_layout.addWidget(secondary)
        preview.add_widget(row)

        badges = QWidget()
        badges.setProperty("transparentBg", True)
        badges_layout = QHBoxLayout(badges)
        badges_layout.setContentsMargins(0, 0, 0, 0)
        badges_layout.setSpacing(8)
        badges_layout.addWidget(make_status_label("идёт"))
        badges_layout.addWidget(make_status_label("внимание", warning=True))
        badges_layout.addStretch(1)
        preview.add_widget(badges)
        preview.add_stretch(1)
        root.addWidget(preview, 2)

    def _apply(self) -> None:
        theme = self._theme_box.currentData()
        accent = self._accent_box.currentData()
        self._vm.save(theme=theme, accent_palette=accent, button_style_preset="soft_glow")
        self._on_apply(theme, accent)

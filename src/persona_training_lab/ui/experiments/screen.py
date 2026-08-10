from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.viewmodels.evaluation import EvaluationText
from persona_training_lab.ui.viewmodels.experiments import ExperimentsViewModel


class ExperimentsScreen(QWidget):
    def __init__(
        self,
        view_model: ExperimentsViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        title, subtitle = self._vm.header_summary()
        self._header_models = (title, subtitle)

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(8)
        self._header_title = QLabel()
        self._header_title.setObjectName("ScreenTitle")
        self._header_subtitle = make_muted_label("")
        header_layout.addWidget(self._header_title)
        header_layout.addWidget(self._header_subtitle)
        root.addWidget(header)

        self._registry = PanelCard("", "")
        self._rows: list[
            tuple[
                QLabel,
                QLabel,
                QLabel,
                str | EvaluationText,
                str | EvaluationText,
                str | EvaluationText,
            ]
        ] = []
        for _exp_id, exp_title, exp_subtitle, exp_status in self._vm.experiments():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(10)
            row_text = QVBoxLayout()
            row_text.setSpacing(4)
            title_label = QLabel()
            subtitle_label = make_muted_label("")
            status_label = make_muted_label("")
            row_text.addWidget(title_label)
            row_text.addWidget(subtitle_label)
            row_layout.addLayout(row_text, 1)
            row_layout.addWidget(status_label)
            self._registry.add_widget(row)
            self._rows.append(
                (
                    title_label,
                    subtitle_label,
                    status_label,
                    exp_title,
                    exp_subtitle,
                    exp_status,
                )
            )

        root.addWidget(self._registry)
        root.addStretch(1)

        self._apply_language()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _render(self, value: str | EvaluationText) -> str:
        if not isinstance(value, EvaluationText):
            return value
        values = {
            key: self._render(item) if isinstance(item, EvaluationText) else item
            for key, item in value.values.items()
        }
        return self._text(value.key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        title, subtitle = self._header_models
        self._header_title.setText(
            self._text(
                "experiments.header.title",
                title=self._render(title),
            )
        )
        self._header_subtitle.setText(self._render(subtitle))
        self._registry.set_title(self._text("experiments.registry.title"))
        self._registry.set_subtitle(
            self._text("experiments.registry.subtitle")
        )
        for (
            title_label,
            subtitle_label,
            status_label,
            title_model,
            subtitle_model,
            status_model,
        ) in self._rows:
            title_label.setText(self._render(title_model))
            subtitle_label.setText(self._render(subtitle_model))
            status_label.setText(self._render(status_model))

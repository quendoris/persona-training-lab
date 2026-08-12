from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.viewmodels.docs import DocText, DocsViewModel


class DocsScreen(QWidget):
    def __init__(
        self,
        view_model: DocsViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization
        self._topics = list(view_model.topics())
        self._context_models = tuple(view_model.context_help())

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        self._topics_card = PanelCard("", "")
        self._topic_list = QListWidget()
        self._topic_list.setObjectName("DocsTopicList")
        self._topic_list.setSpacing(8)
        self._topic_list.setFrameShape(QFrame.Shape.NoFrame)
        for _topic in self._topics:
            self._topic_list.addItem("")
        self._topic_list.currentRowChanged.connect(self._show_topic)
        self._topics_card.add_widget(self._topic_list)
        root.addWidget(self._topics_card, 1)

        self._content_card = PanelCard("", "")
        self._title = QLabel("—")
        self._title.setObjectName("ScreenTitle")
        self._summary = make_muted_label("")
        self._content = QTextEdit()
        self._content.setReadOnly(True)
        self._content.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._content_card.add_widget(self._title)
        self._content_card.add_widget(self._summary)
        self._content_card.add_widget(self._content)
        root.addWidget(self._content_card, 3)

        self._context_card = PanelCard("", "")
        self._next_step = QLabel()
        self._next_step.setWordWrap(True)
        self._next_step.setObjectName("CardTitle")
        self._context_card.add_widget(self._next_step)
        self._context_labels: list[QLabel] = []
        for _model in self._context_models:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            label = make_muted_label("")
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            row_layout.addWidget(label)
            self._context_card.add_widget(row)
            self._context_labels.append(label)
        self._context_card.add_stretch(1)
        root.addWidget(self._context_card, 1)

        self._apply_language()
        if self._topics:
            self._topic_list.setCurrentRow(0)
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _render(self, value: str | DocText) -> str:
        if not isinstance(value, DocText):
            return value
        values = {
            key: self._render(item) if isinstance(item, DocText) else item
            for key, item in value.values.items()
        }
        return self._text(value.key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        self._topics_card.set_title(self._text("docs.card.topics.title"))
        self._topics_card.set_subtitle(
            self._text("docs.card.topics.subtitle")
        )
        self._content_card.set_title(self._text("docs.card.content.title"))
        self._content_card.set_subtitle(
            self._text("docs.card.content.subtitle")
        )
        self._context_card.set_title(self._text("docs.card.next.title"))
        self._context_card.set_subtitle(
            self._text("docs.card.next.subtitle")
        )

        for index, topic in enumerate(self._topics):
            item = self._topic_list.item(index)
            if item is not None:
                item.setText(self._render(topic.title))
        for label, model in zip(
            self._context_labels,
            self._context_models,
            strict=True,
        ):
            label.setText(self._render(model))

        current = self._topic_list.currentRow()
        if 0 <= current < len(self._topics):
            self._show_topic(current)
        else:
            self._title.setText("—")
            self._summary.setText(self._text("docs.content.select_summary"))
            self._next_step.setText(self._text("docs.next.select"))

    def _show_topic(self, index: int) -> None:
        if index < 0 or index >= len(self._topics):
            return
        topic = self._topics[index]
        self._title.setText(self._render(topic.title))
        self._summary.setText(self._render(topic.summary))
        self._next_step.setText(self._render(topic.next_step))
        self._content.setPlainText(self._render(self._vm.topic_content(topic.path)))

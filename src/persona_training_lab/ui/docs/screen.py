from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QTextEdit, QHBoxLayout, QLabel, QFrame, QVBoxLayout, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.viewmodels.docs import DocsViewModel


class DocsScreen(QWidget):
    def __init__(self, view_model: DocsViewModel) -> None:
        super().__init__()
        self._vm = view_model
        self._topics = list(view_model.topics())

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        topics = PanelCard("Документация", "Живые разделы проекта, которые помогают пройти рабочий маршрут.")
        self._topic_list = QListWidget()
        self._topic_list.setObjectName("DocsTopicList")
        self._topic_list.setSpacing(8)
        self._topic_list.setFrameShape(QListWidget.NoFrame)
        for topic in self._topics:
            self._topic_list.addItem(topic.title)
        self._topic_list.currentRowChanged.connect(self._show_topic)
        topics.add_widget(self._topic_list)
        root.addWidget(topics, 1)

        content = PanelCard("Раздел", "Текст берётся из markdown-файлов в docs/.")
        self._title = QLabel("—")
        self._title.setObjectName("ScreenTitle")
        self._summary = make_muted_label("Выберите раздел слева.")
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        content.add_widget(self._title)
        content.add_widget(self._summary)
        content.add_widget(self._text)
        root.addWidget(content, 3)

        context = PanelCard("Что делать дальше", "Короткие подсказки без лишней мешуры.")
        self._next_step = QLabel("Выберите раздел документации.")
        self._next_step.setWordWrap(True)
        self._next_step.setObjectName("CardTitle")
        context.add_widget(self._next_step)
        for line in view_model.context_help():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            label = make_muted_label(line)
            label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            row_layout.addWidget(label)
            context.add_widget(row)
        context.add_stretch(1)
        root.addWidget(context, 1)

        if self._topics:
            self._topic_list.setCurrentRow(0)

    def _show_topic(self, index: int) -> None:
        if index < 0 or index >= len(self._topics):
            return
        topic = self._topics[index]
        self._title.setText(topic.title)
        self._summary.setText(topic.summary)
        self._next_step.setText(topic.next_step)
        self._text.setPlainText(self._vm.topic_content(topic.path))

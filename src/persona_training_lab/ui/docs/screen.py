from __future__ import annotations

from PySide6.QtWidgets import QListWidget, QTextEdit, QHBoxLayout, QLabel, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.viewmodels.docs import DocsViewModel


class DocsScreen(QWidget):
    def __init__(self, view_model: DocsViewModel) -> None:
        super().__init__()
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        topics = PanelCard("Разделы docs", "Встроенная справка должна помогать в работе, а не быть мёртвым приложением сбоку.")
        topic_list = QListWidget()
        topic_list.setObjectName("DocsTopicList")
        topic_list.setSpacing(8)
        topic_list.setFrameShape(QListWidget.NoFrame)
        for line in view_model.topics():
            topic_list.addItem(line)
        topics.add_widget(topic_list)
        root.addWidget(topics, 1)

        content = PanelCard("Быстрая шпаргалка", "Та самая встроенная помощь по использованию программы.")
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText("\n".join(f"• {line}" for line in view_model.quick_reference()))
        content.add_widget(text)
        root.addWidget(content, 2)

        context = PanelCard("Подсказка по контексту", "Связанная помощь должна жить рядом с текущим действием.")
        for line in view_model.context_help():
            label = QLabel(line)
            label.setWordWrap(True)
            context.add_widget(label)
        context.add_stretch(1)
        root.addWidget(context, 1)

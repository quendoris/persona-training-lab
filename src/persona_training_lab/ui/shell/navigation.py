from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem


class NavigationRail(QListWidget):
    screen_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.add_screen("dashboard", "Панель")
        self.add_screen("profiles", "Профили")
        self.add_screen("datasets", "Датасеты")
        self.add_screen("training", "Обучение")
        self.add_screen("snapshots", "Снимки")
        self.add_screen("tests", "Тесты")
        self.add_screen("analysis", "Анализ")
        self.add_screen("style", "Оформление")
        self.add_screen("docs", "Документация")
        self.currentItemChanged.connect(self._emit_screen)
        self.setCurrentRow(0)

    def add_screen(self, screen_id: str, title: str) -> None:
        item = QListWidgetItem(title)
        item.setData(256, screen_id)
        self.addItem(item)

    def _emit_screen(self) -> None:
        item = self.currentItem()
        if item is not None:
            self.screen_selected.emit(item.data(256))

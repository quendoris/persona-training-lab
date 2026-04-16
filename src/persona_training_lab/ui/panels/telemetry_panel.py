from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


@dataclass(slots=True, frozen=True)
class TelemetryItem:
    short_label: str
    full_label: str
    value: int
    tooltip: str


class _VerticalMetric(QFrame):
    def __init__(self, item: TelemetryItem) -> None:
        super().__init__()
        self.setToolTip(item.tooltip)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        track = QFrame()
        track.setObjectName("TelemetryBarTrack")
        track.setFixedSize(28, 86)

        fill = QFrame(track)
        fill.setObjectName("TelemetryBarFill")
        height = max(28, int(86 * item.value / 100))
        fill.setGeometry(0, 86 - height, 28, height)
        fill.show()

        layout.addWidget(track, 0, Qt.AlignHCenter)
        caption = QLabel(item.short_label)
        caption.setObjectName("TelemetryChip")
        caption.setAlignment(Qt.AlignCenter)
        caption.setMinimumWidth(42)
        caption.setFixedHeight(24)
        layout.addWidget(caption, 0, Qt.AlignHCenter)


class _HorizontalMetric(QFrame):
    def __init__(self, item: TelemetryItem) -> None:
        super().__init__()
        self.setToolTip(item.tooltip)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = QLabel(item.full_label)
        label.setObjectName("TelemetryChip")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumWidth(64)
        label.setFixedHeight(24)
        layout.addWidget(label)

        track = QFrame()
        track.setObjectName("TelemetryBarTrack")
        track.setMinimumHeight(28)
        track.setMaximumHeight(28)
        track.setFixedWidth(184)

        fill = QFrame(track)
        fill.setObjectName("TelemetryBarFill")
        width = max(28, int(184 * item.value / 100))
        fill.setGeometry(0, 0, width, 28)
        fill.show()

        layout.addWidget(track)
        value_label = QLabel(f"{item.value}%")
        value_label.setObjectName("TelemetryCaption")
        layout.addWidget(value_label)
        layout.addStretch(1)


class TelemetryPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self._items = [
            TelemetryItem("ГП", "ГП", 76, "Нагрузка графического процессора: 76% | 63°C | сеанс стабилен"),
            TelemetryItem("ВП", "ВП", 92, "Видеопамять: 14.8 / 16 ГБ | запас небольшой, но стабильный"),
            TelemetryItem("ОЗУ", "ОЗУ", 58, "Оперативная память: 56 / 96 ГБ | комфортный запас"),
            TelemetryItem("Диск", "Диск", 44, "Нагрузка на диск: умеренная | checkpoints пишутся безопасно"),
            TelemetryItem("Ток", "Ток", 68, "Скорость генерации: 61 ток/с | стабильный поток"),
            TelemetryItem("Шаг", "Шаг", 71, "Время шага: 182 мс | аномалий не обнаружено"),
            TelemetryItem("Риск", "Риск", 23, "Давление по рискам низкое | есть только мягкое предупреждение"),
            TelemetryItem("В/В", "В/В", 37, "Запись артефактов идёт без блокировок"),
        ]
        self._mode: str | None = None

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(14, 14, 14, 14)
        self._root.setSpacing(10)

        self._title = QLabel("Телеметрия")
        self._subtitle = QLabel("Наведи на столбик, чтобы увидеть подробности по конкретной метрике.")
        self._subtitle.setObjectName("MutedText")
        self._root.addWidget(self._title)
        self._root.addWidget(self._subtitle)

        self._content = QWidget()
        self._content.setProperty("transparentBg", True)
        self._root.addWidget(self._content, 1)
        self._rebuild("bottom")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        desired = "side" if self.width() < max(460, self.height() * 0.72) else "bottom"
        if desired != self._mode:
            self._rebuild(desired)

    def _rebuild(self, mode: str) -> None:
        self._mode = mode
        old_layout = self._content.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            old_layout.deleteLater()

        if mode == "side":
            self._subtitle.setText("Панель повернулась вместе с dock-зоной: наведи на строку, чтобы увидеть детали по метрике.")
            outer = QVBoxLayout(self._content)
            outer.setContentsMargins(0, 4, 0, 0)
            outer.setSpacing(0)
            outer.addStretch(1)
            center = QWidget()
            layout = QVBoxLayout(center)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            for item in self._items:
                layout.addWidget(_HorizontalMetric(item))
            outer.addWidget(center, 0, Qt.AlignHCenter)
            outer.addStretch(1)
        else:
            self._subtitle.setText("Наведи на столбик, чтобы увидеть подробности по конкретной метрике.")
            outer = QVBoxLayout(self._content)
            outer.setContentsMargins(0, 4, 0, 0)
            outer.setSpacing(0)
            outer.addStretch(1)
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
            for item in self._items:
                layout.addWidget(_VerticalMetric(item))
            outer.addWidget(row, 0, Qt.AlignLeft)
            outer.addStretch(1)

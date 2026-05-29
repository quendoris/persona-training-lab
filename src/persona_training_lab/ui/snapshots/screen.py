from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QVBoxLayout, QWidget

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.snapshots import SnapshotsViewModel


def _stable_scroll_content(max_height: int = 320) -> tuple[QScrollArea, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setObjectName("StableScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setMinimumHeight(max_height)
    apply_scrollbar_style(scroll)

    outer = QFrame()
    outer.setObjectName("StableScrollShell")
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(14, 14, 14, 14)
    outer_layout.setSpacing(0)

    wrap = QWidget()
    wrap.setObjectName("LifecycleScrollWrap")
    wrap.setStyleSheet("""
        QWidget#LifecycleScrollWrap {
            background: transparent;
            border: none;
        }
    """)

    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    outer_layout.addWidget(wrap)
    scroll.setWidget(outer)
    return scroll, layout


def _elide(text: str, max_len: int = 34) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


class SnapshotsScreen(QWidget):
    def __init__(self, view_model: SnapshotsViewModel) -> None:
        super().__init__()
        self._vm = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)
        self._title = QLabel("Снимки")
        self._title.setObjectName("ScreenTitle")
        self._subtitle = make_muted_label("Зафиксированные версии модели после успешного обучения.")
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._subtitle)
        root.addWidget(header)

        actions = QFrame()
        actions.setObjectName("PanelCardSoft")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(18, 14, 18, 14)
        actions_layout.setSpacing(10)
        self._refresh_btn = QPushButton("Обновить снимки")
        self._refresh_btn.clicked.connect(self._on_refresh_snapshots)
        actions_layout.addWidget(self._refresh_btn)
        actions_layout.addStretch(1)
        root.addWidget(actions)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left_container = QWidget()
        left_container.setFixedWidth(360)
        left = QVBoxLayout(left_container)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(16)
        body.addWidget(left_container, 0)

        registry = PanelCard("Реестр снимков", "Версии модели, зарегистрированные после full fine-tune.")
        self._list = QListWidget()
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._list.itemSelectionChanged.connect(self._on_changed)
        registry.add_widget(self._list)
        left.addWidget(registry, 1)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        self._detail = PanelCard("Сводка снимка", "Снимок теперь читается из реальных model_versions.")
        self._detail_grid = QGridLayout()
        self._detail_grid.setSpacing(12)
        self._detail._layout.addLayout(self._detail_grid)
        center.addWidget(self._detail, 0)

        self._timeline = PanelCard("Жизненный цикл", "Как artifact стал версией модели.")
        self._timeline_scroll, self._timeline_layout = _stable_scroll_content(320)
        self._timeline.add_widget(self._timeline_scroll)
        center.addWidget(self._timeline, 1)

        right_container = QWidget()
        right_container.setFixedWidth(320)
        right = QVBoxLayout(right_container)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(16)
        body.addWidget(right_container, 0)

        self._lineage = PanelCard("Lineage-цепочка", "Связность как основа доверия к снимку.")
        self._lineage_layout = QVBoxLayout()
        self._lineage_layout.setSpacing(10)
        self._lineage._layout.addLayout(self._lineage_layout)
        right.addWidget(self._lineage)

        self._next = PanelCard("Следующий лучший шаг", "Система должна вести дальше.")
        self._next_text = make_muted_label("")
        self._next.add_widget(self._next_text)
        right.addWidget(self._next)
        right.addStretch(1)

        self._populate()
        self._refresh()

    def _populate(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        current_item = None
        for row in self._vm.snapshots:
            item = QListWidgetItem(_elide(row.title))
            item.setData(Qt.ItemDataRole.UserRole, row.snapshot_id)
            item.setToolTip(f"{row.title}\n{row.subtitle}")
            self._list.addItem(item)
            if row.snapshot_id == self._vm.current_snapshot().snapshot_id:
                current_item = item
        if current_item is not None:
            self._list.setCurrentItem(current_item)
        self._list.blockSignals(False)

    def _refresh(self) -> None:
        snap = self._vm.current_snapshot()
        self._title.setText(f"Снимки · {snap.title}")
        self._subtitle.setText(snap.subtitle)

        while self._detail_grid.count():
            item = self._detail_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for index, (key, value) in enumerate(self._vm.detail_metrics()):
            card = QFrame()
            card.setObjectName("PanelCardSoft")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(8)
            label = QLabel(key)
            label.setObjectName("MutedText")
            value_label = QLabel(value)
            value_label.setObjectName("CardTitle")
            value_label.setWordWrap(True)
            layout.addWidget(label)
            layout.addWidget(value_label)
            self._detail_grid.addWidget(card, index // 2, index % 2)

        while self._timeline_layout.count():
            item = self._timeline_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for title, note in self._vm.timeline_rows():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 12, 14, 12)
            rl.setSpacing(12)
            dot = QLabel("")
            dot.setObjectName("LineageIcon")
            dot.setFixedSize(22, 22)
            text_wrap = QVBoxLayout()
            text_wrap.setSpacing(4)
            head = QLabel(title)
            head.setObjectName("CardTitle")
            text_wrap.addWidget(head)
            text_wrap.addWidget(make_muted_label(note))
            rl.addWidget(dot, 0, Qt.AlignTop)
            rl.addLayout(text_wrap, 1)
            self._timeline_layout.addWidget(row)
        self._timeline_layout.addStretch(1)

        while self._lineage_layout.count():
            item = self._lineage_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for entry in self._vm.lineage_rows():
            row = QFrame()
            row.setObjectName("LineageRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(10)
            icon = QLabel("›")
            icon.setObjectName("LineageIcon")
            icon.setFixedSize(20, 20)
            rl.addWidget(icon, 0, Qt.AlignVCenter)
            label = QLabel(entry)
            label.setWordWrap(True)
            rl.addWidget(label, 1)
            self._lineage_layout.addWidget(row)
        self._lineage_layout.addStretch(1)
        self._next_text.setText(self._vm.next_step())

    def _on_refresh_snapshots(self) -> None:
        self._vm.refresh()
        self._populate()
        self._refresh()

    def _on_changed(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        snapshot_id = item.data(Qt.ItemDataRole.UserRole)
        self._vm.select_snapshot(snapshot_id)
        self._refresh()

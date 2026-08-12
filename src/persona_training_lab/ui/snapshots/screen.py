from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.snapshots import (
    SnapshotText,
    SnapshotValue,
    SnapshotsViewModel,
)


def _stable_scroll_content(
    max_height: int = 320,
) -> tuple[QScrollArea, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setObjectName("StableScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    scroll.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    scroll.setMinimumHeight(max_height)
    apply_scrollbar_style(scroll)

    outer = QFrame()
    outer.setObjectName("StableScrollShell")
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(14, 14, 14, 14)
    outer_layout.setSpacing(0)

    wrap = QWidget()
    wrap.setObjectName("LifecycleScrollWrap")
    wrap.setStyleSheet(
        """
        QWidget#LifecycleScrollWrap {
            background: transparent;
            border: none;
        }
        """
    )

    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    outer_layout.addWidget(wrap)
    scroll.setWidget(outer)
    return scroll, layout


def _elide(text: str, max_len: int = 34) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


class SnapshotsScreen(QWidget):
    def __init__(
        self,
        view_model: SnapshotsViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)
        self._title = QLabel()
        self._title.setObjectName("ScreenTitle")
        self._subtitle = make_muted_label("")
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._subtitle)
        root.addWidget(header)

        actions = QFrame()
        actions.setObjectName("PanelCardSoft")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(18, 14, 18, 14)
        actions_layout.setSpacing(10)
        self._refresh_btn = QPushButton()
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

        self._registry = PanelCard("", "")
        self._list = QListWidget()
        self._list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        self._list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._list.itemSelectionChanged.connect(self._on_changed)
        self._registry.add_widget(self._list)
        left.addWidget(self._registry, 1)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        self._detail = PanelCard("", "")
        self._detail_grid = QGridLayout()
        self._detail_grid.setSpacing(12)
        self._detail._layout.addLayout(self._detail_grid)
        center.addWidget(self._detail, 0)

        self._timeline = PanelCard("", "")
        self._timeline_scroll, self._timeline_layout = (
            _stable_scroll_content(320)
        )
        self._timeline.add_widget(self._timeline_scroll)
        center.addWidget(self._timeline, 1)

        right_container = QWidget()
        right_container.setFixedWidth(320)
        right = QVBoxLayout(right_container)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(16)
        body.addWidget(right_container, 0)

        self._lineage = PanelCard("", "")
        self._lineage_layout = QVBoxLayout()
        self._lineage_layout.setSpacing(10)
        self._lineage._layout.addLayout(self._lineage_layout)
        right.addWidget(self._lineage)

        self._next = PanelCard("", "")
        self._next_text = make_muted_label("")
        self._next.add_widget(self._next_text)
        right.addWidget(self._next)
        right.addStretch(1)

        self._apply_language()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _render(self, value: SnapshotValue | object) -> str:
        if not isinstance(value, SnapshotText):
            return str(value)
        rendered_values = {
            key: self._render(item)
            for key, item in value.values.items()
        }
        return self._text(value.key, **rendered_values)

    def _apply_language(self, _locale: str = "") -> None:
        self._refresh_btn.setText(
            self._text("snapshots.action.refresh")
        )
        self._registry.set_title(
            self._text("snapshots.card.registry.title")
        )
        self._registry.set_subtitle(
            self._text("snapshots.card.registry.subtitle")
        )
        self._detail.set_title(
            self._text("snapshots.card.detail.title")
        )
        self._detail.set_subtitle(
            self._text("snapshots.card.detail.subtitle")
        )
        self._timeline.set_title(
            self._text("snapshots.card.timeline.title")
        )
        self._timeline.set_subtitle(
            self._text("snapshots.card.timeline.subtitle")
        )
        self._lineage.set_title(
            self._text("snapshots.card.lineage.title")
        )
        self._lineage.set_subtitle(
            self._text("snapshots.card.lineage.subtitle")
        )
        self._next.set_title(
            self._text("snapshots.card.next.title")
        )
        self._next.set_subtitle(
            self._text("snapshots.card.next.subtitle")
        )
        self._populate()
        self._refresh()

    def _populate(self) -> None:
        current_id = self._vm.current_snapshot().snapshot_id
        self._list.blockSignals(True)
        self._list.clear()
        current_item: QListWidgetItem | None = None
        for row in self._vm.snapshots:
            title = self._render(self._vm.row_title_model(row))
            item = QListWidgetItem(_elide(title))
            item.setData(Qt.ItemDataRole.UserRole, row.snapshot_id)
            item.setToolTip(
                self._render(self._vm.row_tooltip_model(row))
            )
            self._list.addItem(item)
            if row.snapshot_id == current_id:
                current_item = item
        if current_item is not None:
            self._list.setCurrentItem(current_item)
        self._list.blockSignals(False)

    def _refresh(self) -> None:
        self._title.setText(self._render(self._vm.header_title_model()))
        self._subtitle.setText(
            self._render(self._vm.header_subtitle_model())
        )

        self._clear_layout(self._detail_grid)
        for index, metric in enumerate(self._vm.metric_models()):
            card = QFrame()
            card.setObjectName("PanelCardSoft")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(8)
            label = QLabel(self._render(metric.title))
            label.setObjectName("MutedText")
            value_label = QLabel(self._render(metric.value))
            value_label.setObjectName("CardTitle")
            value_label.setWordWrap(True)
            note_label = make_muted_label(self._render(metric.note))
            layout.addWidget(label)
            layout.addWidget(value_label)
            layout.addWidget(note_label)
            self._detail_grid.addWidget(card, index // 2, index % 2)

        self._clear_layout(self._timeline_layout)
        for timeline_item in self._vm.timeline_models():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 12, 14, 12)
            row_layout.setSpacing(12)
            dot = QLabel("")
            dot.setObjectName("LineageIcon")
            dot.setFixedSize(22, 22)
            text_wrap = QVBoxLayout()
            text_wrap.setSpacing(4)
            head = QLabel(self._render(timeline_item.title))
            head.setObjectName("CardTitle")
            text_wrap.addWidget(head)
            text_wrap.addWidget(
                make_muted_label(self._render(timeline_item.note))
            )
            row_layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            row_layout.addLayout(text_wrap, 1)
            self._timeline_layout.addWidget(row)
        self._timeline_layout.addStretch(1)

        self._clear_layout(self._lineage_layout)
        for entry in self._vm.lineage_models():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(10)
            icon = QLabel("›")
            icon.setObjectName("LineageIcon")
            icon.setFixedSize(20, 20)
            row_layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)
            label = QLabel(self._render(entry))
            label.setWordWrap(True)
            row_layout.addWidget(label, 1)
            self._lineage_layout.addWidget(row)
        self._lineage_layout.addStretch(1)
        self._next_text.setText(
            self._render(self._vm.next_step_model())
        )

    @staticmethod
    def _clear_layout(layout: QGridLayout | QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _on_refresh_snapshots(self) -> None:
        self._vm.refresh()
        self._apply_language()

    def _on_changed(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        snapshot_id = item.data(Qt.ItemDataRole.UserRole)
        self._vm.select_snapshot(str(snapshot_id))
        self._refresh()

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.datasets import DatasetsViewModel


def _stable_scroll_grid(max_height: int = 320) -> tuple[QScrollArea, QFrame, QGridLayout]:
    scroll = QScrollArea()
    scroll.setObjectName("StableScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setMinimumHeight(max_height)
    apply_scrollbar_style(scroll)
    scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    wrap = QFrame()
    wrap.setObjectName("StableScrollShell")

    layout = QVBoxLayout(wrap)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(0)

    grid_wrap = QWidget()
    grid_wrap.setObjectName("ValidationGridWrap")
    grid_wrap.setProperty("transparentBg", True)
    grid = QGridLayout(grid_wrap)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(12)

    layout.addWidget(grid_wrap)
    layout.addStretch(1)
    scroll.setWidget(wrap)
    return scroll, wrap, grid


def _elide(text: str, max_len: int = 34) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


class DatasetsScreen(QWidget):
    def __init__(self, view_model: DatasetsViewModel) -> None:
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
        self._title = QLabel("Датасеты")
        self._title.setObjectName("ScreenTitle")
        self._subtitle = make_muted_label(
            "Versioned datasets, проверка и readiness для обучения личности."
        )
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._subtitle)
        root.addWidget(header)

        actions = QFrame()
        actions.setObjectName("PanelCardSoft")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(18, 16, 18, 16)
        actions_layout.setSpacing(12)
        for text, secondary in [
            ("Добавить датасет", False),
            ("Проверить датасет", False),
            ("Одобрить для обучения", True),
            ("Сравнить версии", True),
        ]:
            button = QPushButton(text)
            if secondary:
                button.setObjectName("SecondaryButton")
            actions_layout.addWidget(button)
            if text == "Добавить датасет":
                self._add_dataset_btn = button
            if text == "Проверить датасет":
                self._validate_dataset_btn = button
        actions_layout.addStretch(1)
        root.addWidget(actions)
        self._add_dataset_btn.clicked.connect(self._on_add_dataset)
        self._validate_dataset_btn.clicked.connect(self._on_validate_dataset)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left_container = QWidget()
        left_container.setFixedWidth(320)
        left = QVBoxLayout(left_container)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(16)
        body.addWidget(left_container, 0)

        self._datasets_card = PanelCard(
            "Реестр датасетов",
            "Небольшие, но сильные curated-наборы вместо шумного массива.",
        )
        self._datasets_list = QListWidget()
        self._datasets_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._datasets_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._datasets_list.setUniformItemSizes(True)
        self._datasets_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._datasets_list.itemSelectionChanged.connect(self._on_dataset_changed)
        self._datasets_card.add_widget(self._datasets_list)
        left.addWidget(self._datasets_card)

        self._versions_card = PanelCard(
            "Версии",
            "Работаем только с конкретной dataset version, а не с плавающим набором вообще.",
        )
        self._versions_list = QListWidget()
        self._versions_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._versions_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._versions_list.setUniformItemSizes(True)
        self._versions_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._versions_list.itemSelectionChanged.connect(self._on_version_changed)
        self._versions_card.add_widget(self._versions_list)
        left.addWidget(self._versions_card)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        self._preview_card = PanelCard(
            "Предпросмотр записей",
            "Короткий взгляд на структуру и качество выбранной версии.",
        )
        self._preview_card.setMinimumWidth(800)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["ID", "Вход", "Черты", "Качество"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setAlternatingRowColors(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._table.setWordWrap(True)
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._preview_card.add_widget(self._table)
        self._preview_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        center.addWidget(self._preview_card, 1)

        self._validation_card = PanelCard(
            "Результат проверки",
            "Сильная проверка должна быть понятной, а не просто зелёной галочкой.",
        )
        self._validation_scroll, self._validation_wrap, self._validation_grid = _stable_scroll_grid(
            380
        )
        self._validation_scroll.setMinimumHeight(320)
        self._validation_card.add_widget(self._validation_scroll)
        self._validation_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        center.addWidget(self._validation_card, 1)

        right_container = QWidget()
        right_container.setFixedWidth(320)
        right = QVBoxLayout(right_container)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(16)
        body.addWidget(right_container, 0)

        self._summary_card = PanelCard("Сводка версии", "Быстрый контекст без прыжков между окнами.")
        self._summary_rows = QVBoxLayout()
        self._summary_rows.setSpacing(10)
        self._summary_card._layout.addLayout(self._summary_rows)
        right.addWidget(self._summary_card)

        self._quality_card = PanelCard("Качество и готовность", "Что это за версия и что с ней делать дальше.")
        self._quality_summary = make_muted_label("")
        self._quality_card.add_widget(self._quality_summary)
        self._next_step = QFrame()
        self._next_step.setObjectName("WarningBlock")
        next_step_layout = QVBoxLayout(self._next_step)
        next_step_layout.setContentsMargins(14, 12, 14, 12)
        next_step_layout.setSpacing(8)
        next_step_layout.addWidget(QLabel("Следующий лучший шаг"))
        self._next_step_text = make_muted_label("")
        next_step_layout.addWidget(self._next_step_text)
        self._quality_card.add_widget(self._next_step)
        right.addWidget(self._quality_card)
        right.addStretch(1)

        self._populate_datasets()
        self._refresh_all()

    def _populate_datasets(self) -> None:
        self._datasets_list.clear()
        current_id = self._vm.current_dataset().dataset_id
        current_item = None
        for dataset_id, title, status, version_count in self._vm.datasets():
            display = _elide(f"{title}  ·  {version_count} верс.", 30)
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, dataset_id)
            item.setToolTip(f"{title}\nСтатус активной версии: {status}")
            self._datasets_list.addItem(item)
            if dataset_id == current_id:
                current_item = item
        if current_item is not None:
            self._datasets_list.setCurrentItem(current_item)

    def _populate_versions(self) -> None:
        self._versions_list.clear()
        current_version_id = self._vm.current_version().version_id
        current_item = None
        for version_id, label, status, records in self._vm.versions():
            full = f"{label}  ·  {status}  ·  {records} записей"
            item = QListWidgetItem(_elide(full, 32))
            item.setToolTip(full)
            item.setData(Qt.ItemDataRole.UserRole, version_id)
            self._versions_list.addItem(item)
            if version_id == current_version_id:
                current_item = item
        if current_item is not None:
            self._versions_list.setCurrentItem(current_item)

    def _refresh_header(self) -> None:
        title, subtitle = self._vm.header_summary()
        self._title.setText(f"Датасеты · {title}")
        self._subtitle.setText(subtitle)

    def _refresh_table(self) -> None:
        version = self._vm.current_version()
        self._table.setRowCount(len(version.preview_rows))
        for row_index, row in enumerate(version.preview_rows):
            values = [row.row_id, row.input_summary, row.traits, row.quality]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row_index, col_index, item)
        self._table.resizeColumnsToContents()
        self._table.setColumnWidth(1, max(self._table.columnWidth(1), 240))
        self._table.setColumnWidth(2, max(self._table.columnWidth(2), 200))

    def _refresh_validation(self) -> None:
        while self._validation_grid.count():
            item = self._validation_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        signals = self._vm.current_version().validation_signals
        for index, signal in enumerate(signals):
            card = QFrame()
            card.setObjectName("PanelCardSoft")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(8)

            top = QHBoxLayout()
            top.addWidget(QLabel(signal.title))
            top.addStretch(1)

            if signal.state == "warning":
                badge = make_status_label("внимание", warning=True)
            elif signal.state == "ok":
                badge = make_status_label("ok")
            else:
                badge = QLabel("заметка")
                badge.setObjectName("TelemetryChip")

            top.addWidget(badge)
            layout.addLayout(top)
            layout.addWidget(make_muted_label(signal.body))
            self._validation_grid.addWidget(card, index // 2, index % 2)

        self._validation_grid.setRowStretch((len(signals) + 1) // 2, 1)

    def _refresh_summary(self) -> None:
        while self._summary_rows.count():
            item = self._summary_rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for key, value in self._vm.right_summary():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(10)

            left = QLabel(key)
            left.setObjectName("MutedText")
            right = QLabel(value)
            right.setWordWrap(False)
            right.setMinimumWidth(0)

            layout.addWidget(left)
            layout.addStretch(1)
            layout.addWidget(right, 0, Qt.AlignmentFlag.AlignRight)
            self._summary_rows.addWidget(row)

        version = self._vm.current_version()
        self._quality_summary.setText(version.quality_summary)
        self._next_step_text.setText(self._vm.next_step())

    def _refresh_all(self) -> None:
        self._populate_versions()
        self._refresh_header()
        self._refresh_table()
        self._refresh_validation()
        self._refresh_summary()

    def _on_dataset_changed(self) -> None:
        item = self._datasets_list.currentItem()
        if item is None:
            return
        dataset_id = item.data(Qt.ItemDataRole.UserRole)
        self._vm.select_dataset(dataset_id)
        self._refresh_all()

    def _on_version_changed(self) -> None:
        item = self._versions_list.currentItem()
        if item is None:
            return
        version_id = item.data(Qt.ItemDataRole.UserRole)
        self._vm.select_version(version_id)
        self._refresh_header()
        self._refresh_table()
        self._refresh_validation()
        self._refresh_summary()

    def _on_add_dataset(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите JSONL датасет",
            "",
            "JSONL (*.jsonl)",
        )
        if not file_path:
            return
        ok, message = self._vm.add_dataset_from_path(file_path)
        self._subtitle.setText(message)
        if ok:
            self._populate_datasets()
            self._refresh_all()

    def _on_validate_dataset(self) -> None:
        ok, message = self._vm.validate_current_dataset()
        self._subtitle.setText(message)
        self._populate_datasets()
        self._refresh_all()

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QCloseEvent
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
from persona_training_lab.ui.components.panels import (
    make_muted_label,
    make_status_label,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.themes.manager import apply_scrollbar_style
from persona_training_lab.ui.viewmodels.datasets import (
    DatasetText,
    DatasetsViewModel,
)


def _stable_scroll_grid(
    max_height: int = 320,
) -> tuple[QScrollArea, QFrame, QGridLayout]:
    scroll = QScrollArea()
    scroll.setObjectName("StableScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setMinimumHeight(max_height)
    apply_scrollbar_style(scroll)
    scroll.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )

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


class _DatasetActionWorker(QObject):
    finished = Signal(bool)

    def __init__(self, vm: DatasetsViewModel, action: str) -> None:
        super().__init__()
        self._vm = vm
        self._action = action

    def run(self) -> None:
        if self._action == "validate":
            ok, _message = self._vm.validate_current_dataset()
        elif self._action == "approve":
            ok, _message = self._vm.approve_current_dataset()
        else:
            ok = False
        self.finished.emit(ok)


class DatasetsScreen(QWidget):
    def __init__(
        self,
        view_model: DatasetsViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization
        self._dataset_thread: QThread | None = None
        self._dataset_worker: _DatasetActionWorker | None = None

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
        actions_layout.setContentsMargins(18, 16, 18, 16)
        actions_layout.setSpacing(12)

        self._add_dataset_btn = QPushButton()
        actions_layout.addWidget(self._add_dataset_btn)
        self._validate_dataset_btn = QPushButton()
        actions_layout.addWidget(self._validate_dataset_btn)
        self._approve_dataset_btn = QPushButton()
        self._approve_dataset_btn.setObjectName("SecondaryButton")
        actions_layout.addWidget(self._approve_dataset_btn)
        self._compare_versions_btn = QPushButton()
        self._compare_versions_btn.setObjectName("SecondaryButton")
        self._compare_versions_btn.setEnabled(False)
        actions_layout.addWidget(self._compare_versions_btn)
        actions_layout.addStretch(1)
        root.addWidget(actions)
        self._add_dataset_btn.clicked.connect(self._on_add_dataset)
        self._validate_dataset_btn.clicked.connect(self._on_validate_dataset)
        self._approve_dataset_btn.clicked.connect(self._on_approve_dataset)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left_container = QWidget()
        left_container.setFixedWidth(320)
        left = QVBoxLayout(left_container)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(16)
        body.addWidget(left_container, 0)

        self._datasets_card = PanelCard("", "")
        self._datasets_list = QListWidget()
        self._datasets_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._datasets_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._datasets_list.setUniformItemSizes(True)
        self._datasets_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._datasets_list.itemSelectionChanged.connect(
            self._on_dataset_changed
        )
        self._datasets_card.add_widget(self._datasets_list)
        left.addWidget(self._datasets_card)

        self._versions_card = PanelCard("", "")
        self._versions_list = QListWidget()
        self._versions_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._versions_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._versions_list.setUniformItemSizes(True)
        self._versions_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._versions_list.itemSelectionChanged.connect(
            self._on_version_changed
        )
        self._versions_card.add_widget(self._versions_list)
        left.addWidget(self._versions_card)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        self._preview_card = PanelCard("", "")
        self._preview_card.setMinimumWidth(800)
        self._table = QTableWidget(0, 4)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self._table.setAlternatingRowColors(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._table.setWordWrap(True)
        self._table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._preview_card.add_widget(self._table)
        self._preview_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        center.addWidget(self._preview_card, 1)

        self._validation_card = PanelCard("", "")
        (
            self._validation_scroll,
            self._validation_wrap,
            self._validation_grid,
        ) = _stable_scroll_grid(380)
        self._validation_scroll.setMinimumHeight(320)
        self._validation_card.add_widget(self._validation_scroll)
        self._validation_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        center.addWidget(self._validation_card, 1)

        right_container = QWidget()
        right_container.setFixedWidth(320)
        right = QVBoxLayout(right_container)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(16)
        body.addWidget(right_container, 0)

        self._summary_card = PanelCard("", "")
        self._summary_rows = QVBoxLayout()
        self._summary_rows.setSpacing(10)
        self._summary_card._layout.addLayout(self._summary_rows)
        right.addWidget(self._summary_card)

        self._quality_card = PanelCard("", "")
        self._quality_summary = make_muted_label("")
        self._quality_card.add_widget(self._quality_summary)
        self._next_step = QFrame()
        self._next_step.setObjectName("WarningBlock")
        next_step_layout = QVBoxLayout(self._next_step)
        next_step_layout.setContentsMargins(14, 12, 14, 12)
        next_step_layout.setSpacing(8)
        self._next_step_title = QLabel()
        next_step_layout.addWidget(self._next_step_title)
        self._next_step_text = make_muted_label("")
        next_step_layout.addWidget(self._next_step_text)
        self._quality_card.add_widget(self._next_step)
        right.addWidget(self._quality_card)
        right.addStretch(1)

        self._apply_static_text()
        self._populate_datasets()
        self._refresh_all()
        if localization is not None:
            localization.language_changed.connect(self._refresh_language)

    def _text(
        self,
        key: str,
        *,
        count: int | None = None,
        **values: object,
    ) -> str:
        return localized_text(
            self._localization,
            key,
            count=count,
            **values,
        )

    def _render(self, value: object) -> str:
        if isinstance(value, DatasetText):
            rendered_values = {
                key: self._render(item)
                if isinstance(item, DatasetText)
                else item
                for key, item in value.values.items()
            }
            count_value = rendered_values.pop("count", None)
            count = count_value if isinstance(count_value, int) else None
            return self._text(
                value.key,
                count=count,
                **rendered_values,
            )
        return str(value)

    def _apply_static_text(self) -> None:
        self._add_dataset_btn.setText(self._text("datasets.action.add"))
        self._validate_dataset_btn.setText(
            self._text("datasets.action.validate")
        )
        self._approve_dataset_btn.setText(
            self._text("datasets.action.approve")
        )
        self._compare_versions_btn.setText(
            self._text("datasets.action.compare")
        )
        self._compare_versions_btn.setToolTip(
            self._text("datasets.action.compare_unavailable")
        )
        self._datasets_card.set_title(
            self._text("datasets.card.registry.title")
        )
        self._datasets_card.set_subtitle(
            self._text("datasets.card.registry.description")
        )
        self._versions_card.set_title(
            self._text("datasets.card.versions.title")
        )
        self._versions_card.set_subtitle(
            self._text("datasets.card.versions.description")
        )
        self._preview_card.set_title(
            self._text("datasets.card.preview.title")
        )
        self._preview_card.set_subtitle(
            self._text("datasets.card.preview.description")
        )
        self._validation_card.set_title(
            self._text("datasets.card.validation.title")
        )
        self._validation_card.set_subtitle(
            self._text("datasets.card.validation.description")
        )
        self._summary_card.set_title(
            self._text("datasets.card.summary.title")
        )
        self._summary_card.set_subtitle(
            self._text("datasets.card.summary.description")
        )
        self._quality_card.set_title(
            self._text("datasets.card.quality.title")
        )
        self._quality_card.set_subtitle(
            self._text("datasets.card.quality.description")
        )
        self._next_step_title.setText(
            self._text("datasets.next_step.title")
        )
        self._table.setHorizontalHeaderLabels(
            [
                "ID",
                self._text("datasets.table.input"),
                self._text("datasets.table.schema"),
                self._text("datasets.table.status"),
            ]
        )

    def _refresh_language(self, _locale: str = "") -> None:
        self._apply_static_text()
        self._populate_datasets()
        self._refresh_all()

    def _display_dataset_title(self, dataset_id: str, title: str) -> str:
        if dataset_id == "datasets_empty":
            return self._text("datasets.title")
        return title

    def _populate_datasets(self) -> None:
        self._datasets_list.clear()
        current_id = self._vm.current_dataset().dataset_id
        current_item = None
        for dataset in self._vm.dataset_views():
            title = self._display_dataset_title(
                dataset.dataset_id,
                dataset.title,
            )
            version = dataset.versions[0]
            versions = self._text(
                "datasets.count.versions",
                count=len(dataset.versions),
            )
            display = self._text(
                "datasets.dataset.item",
                title=title,
                versions=versions,
            )
            item = QListWidgetItem(_elide(display, 30))
            item.setData(Qt.ItemDataRole.UserRole, dataset.dataset_id)
            item.setToolTip(
                self._text(
                    "datasets.dataset.tooltip",
                    title=title,
                    status=self._render(
                        self._vm.status_text(version.status)
                    ),
                )
            )
            self._datasets_list.addItem(item)
            if dataset.dataset_id == current_id:
                current_item = item
        if current_item is not None:
            self._datasets_list.setCurrentItem(current_item)

    def _populate_versions(self) -> None:
        self._versions_list.clear()
        current_version_id = self._vm.current_version().version_id
        current_item = None
        for version in self._vm.version_views():
            records = self._text(
                "datasets.count.records",
                count=version.record_count,
            )
            full = self._text(
                "datasets.version.item",
                label=version.label,
                status=self._render(self._vm.status_text(version.status)),
                records=records,
            )
            item = QListWidgetItem(_elide(full, 32))
            item.setToolTip(full)
            item.setData(Qt.ItemDataRole.UserRole, version.version_id)
            self._versions_list.addItem(item)
            if version.version_id == current_version_id:
                current_item = item
        if current_item is not None:
            self._versions_list.setCurrentItem(current_item)

    def _refresh_header(self) -> None:
        title, subtitle = self._vm.header_summary_model()
        display_title = self._display_dataset_title(
            self._vm.current_dataset().dataset_id,
            title,
        )
        self._title.setText(
            self._text("datasets.header.title", title=display_title)
        )
        self._subtitle.setText(self._render(subtitle))

    def _refresh_table(self) -> None:
        version = self._vm.current_version()
        self._table.setRowCount(len(version.preview_rows))
        for row_index, row in enumerate(version.preview_rows):
            values = [
                row.row_id,
                self._render(row.input_summary),
                row.traits,
                self._render(row.quality),
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row_index, col_index, item)
        self._table.resizeColumnsToContents()
        self._table.setColumnWidth(
            1,
            max(self._table.columnWidth(1), 280),
        )
        self._table.setColumnWidth(
            2,
            max(self._table.columnWidth(2), 180),
        )

    def _refresh_validation(self) -> None:
        while self._validation_grid.count():
            item = self._validation_grid.takeAt(0)
            if item is None:
                continue
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
            top.addWidget(QLabel(self._render(signal.title)))
            top.addStretch(1)
            if signal.state == "warning":
                badge = make_status_label(
                    self._text("datasets.badge.error"),
                    tone="pending",
                )
            elif signal.state == "ok":
                badge = make_status_label(
                    self._text("datasets.badge.ok")
                )
            else:
                badge = QLabel(self._text("datasets.badge.note"))
                badge.setObjectName("TelemetryChip")
            top.addWidget(badge)
            layout.addLayout(top)
            layout.addWidget(make_muted_label(self._render(signal.body)))
            self._validation_grid.addWidget(
                card,
                index // 2,
                index % 2,
            )
        self._validation_grid.setRowStretch(
            (len(signals) + 1) // 2,
            1,
        )

    def _refresh_summary(self) -> None:
        while self._summary_rows.count():
            item = self._summary_rows.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for key, value in self._vm.right_summary_model():
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(10)
            left = QLabel(self._text(key))
            left.setObjectName("MutedText")
            right = QLabel(self._render(value))
            right.setWordWrap(False)
            right.setMinimumWidth(0)
            layout.addWidget(left)
            layout.addStretch(1)
            layout.addWidget(
                right,
                0,
                Qt.AlignmentFlag.AlignRight,
            )
            self._summary_rows.addWidget(row)
        version = self._vm.current_version()
        self._quality_summary.setText(
            self._render(version.quality_summary)
        )
        self._next_step_text.setText(
            self._render(self._vm.next_step_model())
        )

    def _refresh_all(self) -> None:
        self._populate_versions()
        self._refresh_header()
        self._refresh_table()
        self._refresh_validation()
        self._refresh_summary()

    def _set_dataset_actions_enabled(self, enabled: bool) -> None:
        self._add_dataset_btn.setEnabled(enabled)
        self._validate_dataset_btn.setEnabled(enabled)
        self._approve_dataset_btn.setEnabled(enabled)

    def _begin_dataset_action(self, action: str, label_key: str) -> None:
        if (
            self._dataset_thread is not None
            and self._dataset_thread.isRunning()
        ):
            self._subtitle.setText(self._text("datasets.action.busy"))
            return
        self._subtitle.setText(self._text(label_key))
        self._set_dataset_actions_enabled(False)
        self._dataset_thread = QThread(self)
        self._dataset_worker = _DatasetActionWorker(self._vm, action)
        self._dataset_worker.moveToThread(self._dataset_thread)
        self._dataset_thread.started.connect(self._dataset_worker.run)
        self._dataset_worker.finished.connect(
            self._on_dataset_action_finished
        )
        self._dataset_worker.finished.connect(self._dataset_thread.quit)
        self._dataset_worker.finished.connect(
            self._dataset_worker.deleteLater
        )
        self._dataset_thread.finished.connect(
            self._dataset_thread.deleteLater
        )
        self._dataset_thread.finished.connect(
            self._clear_dataset_worker_refs
        )
        self._dataset_thread.start()

    def _clear_dataset_worker_refs(self) -> None:
        self._dataset_thread = None
        self._dataset_worker = None

    def _on_dataset_action_finished(self, _ok: bool) -> None:
        message = self._vm.current_message()
        if message is not None:
            self._subtitle.setText(self._render(message))
        self._populate_datasets()
        self._refresh_all()
        self._set_dataset_actions_enabled(True)

    def _on_dataset_changed(self) -> None:
        item = self._datasets_list.currentItem()
        if item is None:
            return
        self._vm.select_dataset(item.data(Qt.ItemDataRole.UserRole))
        self._refresh_all()

    def _on_version_changed(self) -> None:
        item = self._versions_list.currentItem()
        if item is None:
            return
        self._vm.select_version(item.data(Qt.ItemDataRole.UserRole))
        self._refresh_header()
        self._refresh_table()
        self._refresh_validation()
        self._refresh_summary()

    def _on_add_dataset(self) -> None:
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self._text("datasets.dialog.select_file"),
            "",
            self._text("datasets.dialog.filter"),
        )
        if not file_path:
            return
        ok, _legacy_message = self._vm.add_dataset_from_path(file_path)
        message = self._vm.current_message()
        if message is not None:
            self._subtitle.setText(self._render(message))
        if ok:
            self._populate_datasets()
            self._refresh_all()

    def _on_validate_dataset(self) -> None:
        self._begin_dataset_action(
            "validate",
            "datasets.action.validating",
        )

    def _on_approve_dataset(self) -> None:
        self._begin_dataset_action(
            "approve",
            "datasets.action.approving",
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if (
            self._dataset_thread is not None
            and self._dataset_thread.isRunning()
        ):
            self._dataset_thread.quit()
            self._dataset_thread.wait(2000)
        super().closeEvent(event)

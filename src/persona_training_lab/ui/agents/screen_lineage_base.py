from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.agents.lineage import LineageVersionNode, build_version_lineage
from persona_training_lab.ui.agents.lineage_state_atomic import AtomicLineageStateStore
from persona_training_lab.ui.agents.version_graph_free_zoom import VersionGraphCanvas
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.viewmodels.agents import AgentDetailView, AgentsViewModel


class AgentsScreen(QWidget):
    """Stable lineage workspace base used by the composed Agents screen."""

    def __init__(self, view_model: AgentsViewModel) -> None:
        super().__init__()
        self._vm = view_model
        self._state = AtomicLineageStateStore()
        self._selected_node_id = "snapshot"
        self._lineage_nodes = self._build_nodes()
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)
        title, subtitle = self._vm.header_summary()
        root.addWidget(self._header(title, subtitle))
        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)
        body.addWidget(self._roles(), 2)
        body.addWidget(self._graph_panel(), 3)
        body.addWidget(self._details(), 2)
        self._select_node(self._graph.current_node_id())
        self._sync_lock_button()
        QTimer.singleShot(0, self._center_current_node)

    def _build_nodes(self) -> tuple[LineageVersionNode, ...]:
        return self._state.apply(build_version_lineage(self._vm.version_nodes()))

    def _header(self, title: str, subtitle: str) -> QFrame:
        header = QFrame()
        header.setObjectName("ShellHeader")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(22, 18, 22, 18)
        label = QLabel(title)
        label.setObjectName("ScreenTitle")
        layout.addWidget(label)
        layout.addWidget(make_muted_label(subtitle))
        return header

    def _roles(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        card = PanelCard("Рабочие роли", "Короткие подсказки по текущему состоянию.")
        for role in self._vm.roles():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            title = QLabel(role.title)
            title.setObjectName("CardTitle")
            row_layout.addWidget(title)
            row_layout.addWidget(make_muted_label(role.mission))
            row_layout.addWidget(make_muted_label(role.next_action))
            if role.status:
                row_layout.addWidget(make_status_label(role.status, "pending"))
            card.add_widget(row)
        layout.addWidget(card)
        layout.addStretch(1)
        return column

    def _graph_panel(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        column.setMinimumSize(0, 0)
        column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._lock_button = self._button("Зафиксировать")
        self._lock_button.clicked.connect(self._toggle_layout_lock)
        flip_button = self._button("Отразить")
        flip_button.clicked.connect(self._toggle_graph_flip)
        current_button = self._button("К актуальной")
        current_button.clicked.connect(self._center_current_node)
        reset_zoom_button = self._button("Сбросить zoom")
        reset_zoom_button.clicked.connect(self._reset_graph_zoom)
        reset_layout_button = self._button("Сбросить раскладку")
        reset_layout_button.clicked.connect(self._reset_graph_layout)
        for button in (
            self._lock_button,
            flip_button,
            current_button,
            reset_zoom_button,
            reset_layout_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self._graph = VersionGraphCanvas(self._lineage_nodes)
        self._graph.node_selected.connect(self._select_node)
        self._graph.zoom_anchor_requested.connect(self._on_graph_zoom_anchor)
        self._graph.pan_requested.connect(self._on_graph_pan)
        if hasattr(self._graph, "workspace_origin_shifted"):
            self._graph.workspace_origin_shifted.connect(self._on_graph_workspace_origin_shift)
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setMinimumSize(0, 0)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._graph)
        scroll.viewport().setMinimumSize(0, 0)
        self._graph_scroll = scroll
        layout.addWidget(scroll, 1)
        return column

    def _details(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        card = PanelCard("Карточка узла", "Параметры и справка выбранной точки.")
        self._detail_title = QLabel("—")
        self._detail_title.setObjectName("CardTitle")
        self._detail_body = QLabel("—")
        self._detail_body.setWordWrap(True)
        card.add_widget(self._detail_title)
        card.add_widget(self._detail_body)
        card.add_widget(QLabel("Проверить"))
        self._checks_layout = QGridLayout()
        card._layout.addLayout(self._checks_layout)
        card.add_widget(QLabel("Справка"))
        self._actions_layout = QGridLayout()
        card._layout.addLayout(self._actions_layout)
        layout.addWidget(card)
        layout.addStretch(1)
        return column

    def _detail_for(self, node_id: str) -> AgentDetailView:
        return self._vm.node_detail(node_id)

    def _select_node(self, node_id: str) -> None:
        self._selected_node_id = node_id
        self._graph.set_selected(node_id)
        self._render_detail(self._detail_for(node_id))

    def _render_detail(self, detail: AgentDetailView) -> None:
        self._detail_title.setText(detail.title)
        self._detail_body.setText(detail.body)
        self._clear_layout(self._checks_layout)
        for index, item in enumerate(detail.checks):
            self._checks_layout.addWidget(
                make_status_label(item, "good"),
                index // 2,
                index % 2,
            )
        self._clear_layout(self._actions_layout)
        for index, item in enumerate(detail.actions):
            self._actions_layout.addWidget(
                make_status_label(item, "pending"),
                index // 2,
                index % 2,
            )

    def _button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(30)
        button.setProperty("secondary", True)
        return button

    def _workflow_button(self, text: str, handler) -> QPushButton:
        button = self._button(text)
        button.clicked.connect(handler)
        return button

    def _node_by_id(self, node_id: str) -> LineageVersionNode | None:
        return next(
            (node for node in self._lineage_nodes if node.node_id == node_id),
            None,
        )

    def _make_current(self) -> None:
        self._state.set_current(self._selected_node_id)
        self._refresh_lineage(center=True)

    def _mark_tone(self, tone: str) -> None:
        self._state.set_tone(self._selected_node_id, tone)
        self._refresh_lineage(center=False)

    def _continue_from_selected(self) -> None:
        self._selected_node_id = self._state.continue_from(self._selected_node_id)
        self._refresh_lineage(center=True)

    def _refresh_lineage(self, center: bool) -> None:
        self._lineage_nodes = self._build_nodes()
        self._graph.set_nodes(self._lineage_nodes)
        self._select_node(self._selected_node_id)
        if center:
            QTimer.singleShot(0, lambda: self._center_on_node(self._selected_node_id))

    def _toggle_layout_lock(self) -> None:
        if not hasattr(self._graph, "set_layout_locked"):
            return
        self._graph.set_layout_locked(not self._graph.layout_locked())
        self._sync_lock_button()

    def _sync_lock_button(self) -> None:
        if not hasattr(self, "_lock_button") or not hasattr(self._graph, "layout_locked"):
            return
        self._lock_button.setText(
            "Разблокировать" if self._graph.layout_locked() else "Зафиксировать"
        )

    def _toggle_graph_flip(self) -> None:
        self._graph.toggle_flipped()
        QTimer.singleShot(0, lambda: self._center_on_node(self._selected_node_id))

    def _center_current_node(self) -> None:
        self._center_on_node(self._graph.current_node_id())

    def _center_on_node(self, node_id: str) -> None:
        center = self._graph.node_center(node_id)
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        hbar.setValue(
            max(0, int(center.x() - self._graph_scroll.viewport().width() / 2))
        )
        vbar.setValue(
            max(0, int(center.y() - self._graph_scroll.viewport().height() / 2))
        )

    def _reset_graph_zoom(self) -> None:
        self._graph.reset_zoom()
        QTimer.singleShot(0, lambda: self._center_on_node(self._selected_node_id))

    def _reset_graph_layout(self) -> None:
        if hasattr(self._graph, "reset_layout"):
            self._graph.reset_layout()
        QTimer.singleShot(0, lambda: self._center_on_node(self._selected_node_id))

    def _on_graph_zoom_anchor(
        self,
        anchor: QPointF,
        old_zoom: float,
        new_zoom: float,
    ) -> None:
        if old_zoom <= 0:
            return
        ratio = new_zoom / old_zoom
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        # anchor is expressed in canvas coordinates. Preserve the point beneath
        # the cursor without multiplying the existing scroll offset twice.
        target_h = hbar.value() + int(round(anchor.x() * (ratio - 1.0)))
        target_v = vbar.value() + int(round(anchor.y() * (ratio - 1.0)))
        QTimer.singleShot(
            0,
            lambda: self._apply_workspace_scroll_shift(target_h, target_v),
        )

    def _on_graph_workspace_origin_shift(self, delta: QPointF) -> None:
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        target_h = hbar.value() + int(round(delta.x()))
        target_v = vbar.value() + int(round(delta.y()))
        QTimer.singleShot(
            0,
            lambda: self._apply_workspace_scroll_shift(target_h, target_v),
        )

    def _apply_workspace_scroll_shift(self, horizontal: int, vertical: int) -> None:
        self._graph_scroll.horizontalScrollBar().setValue(horizontal)
        self._graph_scroll.verticalScrollBar().setValue(vertical)

    def _on_graph_pan(self, delta: QPointF) -> None:
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        hbar.setValue(hbar.value() - int(delta.x()))
        vbar.setValue(vbar.value() - int(delta.y()))

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

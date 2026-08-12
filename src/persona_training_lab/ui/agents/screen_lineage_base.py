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

from persona_training_lab.ui.agents.lineage import (
    LineageVersionNode,
    build_version_lineage,
)
from persona_training_lab.ui.agents.lineage_state_atomic import (
    AtomicLineageStateStore,
)
from persona_training_lab.ui.agents.version_graph_free_zoom import (
    VersionGraphCanvas,
)
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import (
    make_muted_label,
    make_status_label,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import (
    render_user_message,
    text as localized_text,
)
from persona_training_lab.ui.viewmodels.agents_contracts import (
    AgentDetailView,
    AgentText,
)


class AgentsScreen(QWidget):
    """Stable lineage workspace base used by the composed Agents screen."""

    def __init__(
        self,
        view_model,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization
        self._state = AtomicLineageStateStore()
        self._selected_node_id = "snapshot"
        self._lineage_nodes = self._build_nodes()
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)
        root.addWidget(self._header())
        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)
        body.addWidget(self._roles(), 2)
        body.addWidget(self._graph_panel(), 3)
        body.addWidget(self._details(), 2)
        self._select_node(self._graph.current_node_id())
        self._sync_lock_button()
        QTimer.singleShot(0, self._center_current_node)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(
            self._localization,
            key,
            **values,
        )

    def _render_text(self, value: AgentText) -> str:
        return render_user_message(self._localization, value)

    def _build_nodes(self) -> tuple[LineageVersionNode, ...]:
        return self._state.apply(
            build_version_lineage(self._vm.version_nodes())
        )

    def _header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("ShellHeader")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(22, 18, 22, 18)
        self._header_title = QLabel(self._text("agents.header.title"))
        self._header_title.setObjectName("ScreenTitle")
        self._header_subtitle = make_muted_label(
            self._text("agents.header.subtitle")
        )
        layout.addWidget(self._header_title)
        layout.addWidget(self._header_subtitle)
        return header

    def _roles(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        card = PanelCard(
            self._text("agents.roles.title"),
            self._text("agents.roles.subtitle"),
        )
        self._roles_card = card
        for role in self._vm.roles():
            row = QFrame()
            row.setObjectName("LineageRow")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            title = QLabel(self._render_text(role.title))
            title.setObjectName("CardTitle")
            row_layout.addWidget(title)
            row_layout.addWidget(
                make_muted_label(self._render_text(role.mission))
            )
            row_layout.addWidget(
                make_muted_label(self._render_text(role.next_action))
            )
            if role.status:
                row_layout.addWidget(
                    make_status_label(
                        self._render_text(role.status),
                        "pending",
                    )
                )
            card.add_widget(row)
        layout.addWidget(card)
        layout.addStretch(1)
        return column

    def _graph_panel(self) -> QWidget:
        column = QWidget()
        column.setProperty("transparentBg", True)
        column.setMinimumSize(0, 0)
        column.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._lock_button = self._button(
            self._text("agents.graph.lock")
        )
        self._lock_button.clicked.connect(self._toggle_layout_lock)
        self._flip_button = self._button(
            self._text("agents.graph.flip")
        )
        self._flip_button.clicked.connect(self._toggle_graph_flip)
        self._current_button = self._button(
            self._text("agents.graph.current")
        )
        self._current_button.clicked.connect(self._center_current_node)
        self._reset_zoom_button = self._button(
            self._text("agents.graph.reset_zoom")
        )
        self._reset_zoom_button.clicked.connect(self._reset_graph_zoom)
        self._reset_layout_button = self._button(
            self._text("agents.graph.reset_layout")
        )
        self._reset_layout_button.clicked.connect(
            self._reset_graph_layout
        )
        for button in (
            self._lock_button,
            self._flip_button,
            self._current_button,
            self._reset_zoom_button,
            self._reset_layout_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self._graph = VersionGraphCanvas(self._lineage_nodes)
        if hasattr(self._graph, "set_text_renderer"):
            self._graph.set_text_renderer(self._render_text)
        if hasattr(self._graph, "set_action_text_resolver"):
            self._graph.set_action_text_resolver(self._text)
        if hasattr(self._graph, "set_archive_state_resolver"):
            self._graph.set_archive_state_resolver(
                self._state.is_archived
            )
        self._graph.node_selected.connect(self._select_node)
        self._graph.zoom_anchor_requested.connect(
            self._on_graph_zoom_anchor
        )
        self._graph.pan_requested.connect(self._on_graph_pan)
        if hasattr(self._graph, "workspace_origin_shifted"):
            self._graph.workspace_origin_shifted.connect(
                self._on_graph_workspace_origin_shift
            )
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored
        )
        scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        scroll.setMinimumSize(0, 0)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
        )
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
        card = PanelCard(
            self._text("agents.details.node_title"),
            self._text("agents.details.legacy_subtitle"),
        )
        self._details_card = card
        self._detail_title = QLabel("—")
        self._detail_title.setObjectName("CardTitle")
        self._detail_body = QLabel("—")
        self._detail_body.setWordWrap(True)
        card.add_widget(self._detail_title)
        card.add_widget(self._detail_body)
        self._detail_checks_title = QLabel(
            self._text("agents.details.check")
        )
        card.add_widget(self._detail_checks_title)
        self._checks_layout = QGridLayout()
        card._layout.addLayout(self._checks_layout)
        self._detail_help_title = QLabel(
            self._text("agents.details.help")
        )
        card.add_widget(self._detail_help_title)
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
        self._detail_title.setText(self._render_text(detail.title))
        self._detail_body.setText(self._render_text(detail.body))
        self._clear_layout(self._checks_layout)
        for index, item in enumerate(detail.checks):
            self._checks_layout.addWidget(
                make_status_label(
                    self._render_text(item),
                    "good",
                ),
                index // 2,
                index % 2,
            )
        self._clear_layout(self._actions_layout)
        for index, item in enumerate(detail.actions):
            self._actions_layout.addWidget(
                make_status_label(
                    self._render_text(item),
                    "pending",
                ),
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

    def _node_by_id(
        self,
        node_id: str,
    ) -> LineageVersionNode | None:
        return next(
            (
                node
                for node in self._lineage_nodes
                if node.node_id == node_id
            ),
            None,
        )

    def _make_current(self) -> None:
        self._state.set_current(self._selected_node_id)
        self._refresh_lineage(center=True)

    def _mark_tone(self, tone: str) -> None:
        self._state.set_tone(self._selected_node_id, tone)
        self._refresh_lineage(center=False)

    def _continue_from_selected(self) -> None:
        self._selected_node_id = self._state.continue_from(
            self._selected_node_id
        )
        self._refresh_lineage(center=True)

    def _refresh_lineage(self, center: bool) -> None:
        self._lineage_nodes = self._build_nodes()
        self._graph.set_nodes(self._lineage_nodes)
        self._select_node(self._selected_node_id)
        if center:
            QTimer.singleShot(
                0,
                lambda: self._center_on_node(
                    self._selected_node_id
                ),
            )

    def _toggle_layout_lock(self) -> None:
        if not hasattr(self._graph, "set_layout_locked"):
            return
        self._graph.set_layout_locked(
            not self._graph.layout_locked()
        )
        self._sync_lock_button()

    def _sync_lock_button(self) -> None:
        if (
            not hasattr(self, "_lock_button")
            or not hasattr(self._graph, "layout_locked")
        ):
            return
        self._lock_button.setText(
            self._text(
                "agents.graph.unlock"
                if self._graph.layout_locked()
                else "agents.graph.lock"
            )
        )

    def _toggle_graph_flip(self) -> None:
        self._graph.toggle_flipped()
        QTimer.singleShot(
            0,
            lambda: self._center_on_node(self._selected_node_id),
        )

    def _center_current_node(self) -> None:
        self._center_on_node(self._graph.current_node_id())

    def _center_on_node(self, node_id: str) -> None:
        center = self._graph.node_center(node_id)
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        hbar.setValue(
            max(
                0,
                int(
                    center.x()
                    - self._graph_scroll.viewport().width() / 2
                ),
            )
        )
        vbar.setValue(
            max(
                0,
                int(
                    center.y()
                    - self._graph_scroll.viewport().height() / 2
                ),
            )
        )

    def _reset_graph_zoom(self) -> None:
        self._graph.reset_zoom()
        QTimer.singleShot(
            0,
            lambda: self._center_on_node(self._selected_node_id),
        )

    def _reset_graph_layout(self) -> None:
        if hasattr(self._graph, "reset_layout"):
            self._graph.reset_layout()
        QTimer.singleShot(
            0,
            lambda: self._center_on_node(self._selected_node_id),
        )

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
        target_h = hbar.value() + int(
            round(anchor.x() * (ratio - 1.0))
        )
        target_v = vbar.value() + int(
            round(anchor.y() * (ratio - 1.0))
        )
        QTimer.singleShot(
            0,
            lambda: self._apply_workspace_scroll_shift(
                target_h,
                target_v,
            ),
        )

    def _on_graph_workspace_origin_shift(
        self,
        delta: QPointF,
    ) -> None:
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        target_h = hbar.value() + int(round(delta.x()))
        target_v = vbar.value() + int(round(delta.y()))
        QTimer.singleShot(
            0,
            lambda: self._apply_workspace_scroll_shift(
                target_h,
                target_v,
            ),
        )

    def _apply_workspace_scroll_shift(
        self,
        horizontal: int,
        vertical: int,
    ) -> None:
        self._graph_scroll.horizontalScrollBar().setValue(horizontal)
        self._graph_scroll.verticalScrollBar().setValue(vertical)

    def _on_graph_pan(self, delta: QPointF) -> None:
        hbar = self._graph_scroll.horizontalScrollBar()
        vbar = self._graph_scroll.verticalScrollBar()
        hbar.setValue(hbar.value() - int(delta.x()))
        vbar.setValue(vbar.value() - int(delta.y()))

    def _refresh_base_language(self) -> None:
        self._header_title.setText(self._text("agents.header.title"))
        self._header_subtitle.setText(
            self._text("agents.header.subtitle")
        )
        roles_card = getattr(self, "_roles_card", None)
        if roles_card is not None:
            roles_card.set_title(self._text("agents.roles.title"))
            roles_card.set_subtitle(
                self._text("agents.roles.subtitle")
            )
        details_card = getattr(self, "_details_card", None)
        if details_card is not None:
            details_card.set_title(
                self._text("agents.details.node_title")
            )
            details_card.set_subtitle(
                self._text("agents.details.legacy_subtitle")
            )
        if hasattr(self, "_detail_checks_title"):
            self._detail_checks_title.setText(
                self._text("agents.details.check")
            )
        if hasattr(self, "_detail_help_title"):
            self._detail_help_title.setText(
                self._text("agents.details.help")
            )
        for attribute, key in (
            ("_flip_button", "agents.graph.flip"),
            ("_current_button", "agents.graph.current"),
            ("_reset_zoom_button", "agents.graph.reset_zoom"),
            ("_reset_layout_button", "agents.graph.reset_layout"),
        ):
            button = getattr(self, attribute, None)
            if button is not None:
                button.setText(self._text(key))
        self._sync_lock_button()
        graph = getattr(self, "_graph", None)
        if graph is not None:
            graph.update()

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

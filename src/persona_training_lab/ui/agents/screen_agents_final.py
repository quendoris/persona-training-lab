from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from persona_training_lab.ui.agents.screen_history_keyguard import (
    AgentsScreen as _HistoryKeyGuardAgentsScreen,
)
from persona_training_lab.ui.agents.screen_stateful import AgentsScreen as _StatefulAgentsScreen
from persona_training_lab.ui.agents.screen_stateful_fixed import (
    AgentsScreen as _StatefulFixedAgentsScreen,
)


class AgentsScreen(_HistoryKeyGuardAgentsScreen):
    """Final bounded agents layout on top of the stable interaction screen."""

    _ROLES_MIN_WIDTH = 300
    _ROLES_MAX_WIDTH = 390
    _DETAILS_MIN_WIDTH = 390
    _DETAILS_MAX_WIDTH = 560

    def __init__(self, view_model) -> None:
        super().__init__(view_model)
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _roles(self) -> QWidget:
        content = _StatefulAgentsScreen._roles(self)
        self._roles_content = content
        return self._bounded_column_scroll(
            content,
            object_name="AgentsRolesScroll",
            minimum_width=self._ROLES_MIN_WIDTH,
            maximum_width=self._ROLES_MAX_WIDTH,
        )

    def _details(self) -> QWidget:
        content = _StatefulFixedAgentsScreen._details(self)
        self._details_content = content
        self._constrain_text_widgets(content)
        return self._bounded_column_scroll(
            content,
            object_name="AgentsDetailsScroll",
            minimum_width=self._DETAILS_MIN_WIDTH,
            maximum_width=self._DETAILS_MAX_WIDTH,
        )

    def _graph_panel(self) -> QWidget:
        panel = _StatefulAgentsScreen._graph_panel(self)
        panel.setMinimumSize(0, 0)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return panel

    def _render_detail(self, detail) -> None:
        super()._render_detail(detail)
        content = getattr(self, "_details_content", None)
        if content is not None:
            self._constrain_text_widgets(content)

    @staticmethod
    def _bounded_column_scroll(
        content: QWidget,
        *,
        object_name: str,
        minimum_width: int,
        maximum_width: int,
    ) -> QScrollArea:
        content.setMinimumSize(0, 0)
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        scroll = QScrollArea()
        scroll.setObjectName(object_name)
        scroll.setProperty("transparentBg", True)
        scroll.setWidgetResizable(True)
        scroll.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        scroll.setMinimumWidth(minimum_width)
        scroll.setMaximumWidth(maximum_width)
        scroll.setMinimumHeight(0)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content)
        scroll.viewport().setMinimumSize(0, 0)
        scroll.viewport().setProperty("transparentBg", True)
        return scroll

    @staticmethod
    def _constrain_text_widgets(root: QWidget) -> None:
        for label in root.findChildren(QLabel):
            label.setMinimumWidth(0)
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            if label.text() and not label.toolTip():
                label.setToolTip(label.text())

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from persona_training_lab.ui.agents.screen_history_keyguard_sticky import (
    AgentsScreen as _StickyHistoryAgentsScreen,
)
from persona_training_lab.ui.agents.screen_stateful import AgentsScreen as _StatefulAgentsScreen
from persona_training_lab.ui.agents.screen_stateful_fixed import (
    AgentsScreen as _StatefulFixedAgentsScreen,
)


class AgentsScreen(_StickyHistoryAgentsScreen):
    """Final bounded agents layout with stable history-key interaction."""

    _ROLES_MIN_WIDTH = 300
    _ROLES_MAX_WIDTH = 390
    _DETAILS_MIN_WIDTH = 390
    _DETAILS_MAX_WIDTH = 560
    _INTERNAL_WINDOW_DEACTIVATION = QEvent.Type.WindowDeactivate

    def __init__(self, view_model) -> None:
        super().__init__(view_model)
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        # Opening an internal dialog deactivates many child windows without the
        # application actually losing focus. Do not reset a live key gesture for
        # those internal focus transitions.
        if self._is_internal_window_deactivation(event.type()):
            return False
        return super().eventFilter(watched, event)

    @classmethod
    def _is_internal_window_deactivation(cls, event_type: QEvent.Type) -> bool:
        return event_type == cls._INTERNAL_WINDOW_DEACTIVATION

    def _handle_history_key_release(self, key_name: str) -> bool:
        if key_name != "shift":
            return super()._handle_history_key_release(key_name)

        # XKB may hide Shift from logical modifiers during Ctrl+Shift layout
        # switching, but its physical KeyRelease remains authoritative.
        was_control_down = self._history_keys.control_down
        was_strict = self._history_keys.strict_undo_requested
        claimed = self._history_keys.release("shift")
        self._stop_undo_repeat()
        if claimed or was_control_down or was_strict:
            self._block_graph_flip()
        return claimed or (was_control_down and was_strict)

    def _reset_history_gesture(self) -> None:
        state = getattr(self, "_history_keys", None)
        delay = getattr(self, "_undo_repeat_delay", None)
        repeat = getattr(self, "_undo_repeat", None)
        has_activity = bool(
            state is not None
            and (
                state.control_down
                or state.shift_down
                or state.shift_latched
                or state.layout_shift_latched
                or state.z_down
                or state.mode is not None
                or state.strict_undo_requested
            )
        )
        has_activity = has_activity or bool(delay is not None and delay.isActive())
        has_activity = has_activity or bool(repeat is not None and repeat.isActive())
        if not has_activity:
            return
        super()._reset_history_gesture()

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

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.agents.screen_history_diagnostics_compat import (
    AgentsScreen as _DiagnosticsCompatAgentsScreen,
)
from persona_training_lab.ui.agents.screen_stateful import AgentsScreen as _StatefulAgentsScreen
from persona_training_lab.ui.agents.screen_stateful_fixed import (
    AgentsScreen as _StatefulFixedAgentsScreen,
)


class AgentsScreen(_DiagnosticsCompatAgentsScreen):
    """Final bounded layout and persistent input diagnostics for the agents screen."""

    _ROLES_MIN_WIDTH = 300
    _ROLES_MAX_WIDTH = 390
    _DETAILS_MIN_WIDTH = 390
    _DETAILS_MAX_WIDTH = 560
    _DEBUG_AUTOSAVE_DELAY_MS = 120
    _INTERNAL_WINDOW_DEACTIVATION = QEvent.Type.WindowDeactivate

    def __init__(self, view_model) -> None:
        super().__init__(view_model)
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._history_debug_autosave = QTimer(self)
        self._history_debug_autosave.setSingleShot(True)
        self._history_debug_autosave.setInterval(self._DEBUG_AUTOSAVE_DELAY_MS)
        self._history_debug_autosave.timeout.connect(self._autosave_history_debug)
        self._autosave_history_debug()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        # The application-level filter sees WindowDeactivate once for many child
        # widgets when an internal dialog opens. That is not a loss of application
        # focus and must not reset the Ctrl/Shift/Z gesture hundreds of times.
        if event.type() == self._INTERNAL_WINDOW_DEACTIVATION:
            return False
        return super().eventFilter(watched, event)

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
        # Bypass the temporary compatibility wrapper that allowed the column to
        # collapse to a few characters. Build the original content once and put it
        # into a bounded vertical viewport.
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

        root_layout = panel.layout()
        if isinstance(root_layout, QVBoxLayout) and not hasattr(self, "_history_debug_button"):
            debug_button = self._button("Отладка Ctrl+Shift+Z")
            debug_button.setObjectName("HistoryDebugButton")
            debug_button.setToolTip(
                "Открыть журнал событий Ctrl, Shift, Z и фактических переходов истории."
            )
            debug_button.clicked.connect(self._show_history_debug)
            root_layout.insertWidget(1, debug_button, 0, Qt.AlignmentFlag.AlignLeft)
            self._history_debug_button = debug_button
        return panel

    def _render_detail(self, detail) -> None:
        super()._render_detail(detail)
        content = getattr(self, "_details_content", None)
        if content is not None:
            self._constrain_text_widgets(content)

    def _install_history_debug_button(self) -> None:
        # The button is created deterministically inside _graph_panel. Keep the old
        # text-search installer only as a fallback for alternate screen layouts.
        if getattr(self, "_history_debug_button", None) is not None:
            return
        super()._install_history_debug_button()

    def _debug_log(self, category: str, **fields) -> None:
        super()._debug_log(category, **fields)
        timer = getattr(self, "_history_debug_autosave", None)
        if timer is not None:
            timer.start()

    def _autosave_history_debug(self) -> None:
        path = self._history_debug_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._history_debug_dump(), encoding="utf-8")
            self._history_debug_autosave_error = None
        except OSError as exc:
            # Diagnostics must never interfere with the editor itself.
            self._history_debug_autosave_error = str(exc)

    @staticmethod
    def _history_debug_path() -> Path:
        return Path.home() / ".persona_training_lab" / "history_input_debug.log"

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

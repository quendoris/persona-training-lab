from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication, QWidget

from persona_training_lab.ui.agents.history_modifier_snapshot import (
    HistoryModifierSnapshot,
)


@dataclass(frozen=True, slots=True)
class HistoryInputEnvironmentSnapshot:
    """One coherent observation of history-relevant Qt input environment."""

    modifiers: HistoryModifierSnapshot
    input_active: bool


class HistoryInputEnvironment:
    """Capture physical modifiers and owner readiness as one Qt observation."""

    @classmethod
    def capture(cls, owner: QWidget) -> HistoryInputEnvironmentSnapshot:
        app = QApplication.instance()
        typed_app = app if isinstance(app, QApplication) else None
        return HistoryInputEnvironmentSnapshot(
            modifiers=HistoryModifierSnapshot.current(),
            input_active=cls._input_is_active(owner, typed_app),
        )

    @staticmethod
    def _input_is_active(
        owner: QWidget,
        app: QApplication | None,
    ) -> bool:
        if app is None or not owner.isVisible():
            return False

        owner_window = owner.window()
        if not owner_window.isActiveWindow():
            return False
        if app.activeModalWidget() is not None:
            return False

        focus = app.focusWidget()
        return focus is None or focus.window() is owner_window

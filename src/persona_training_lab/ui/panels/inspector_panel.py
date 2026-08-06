from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.panels.localization import text as panel_text


I18N_KEY_PREFIXES = ("inspector.context.",)

_CONTEXT_CHECK_COUNTS: dict[str, int] = {
    "dashboard": 3,
    "datasets": 3,
    "training": 4,
    "snapshots": 3,
    "tests": 4,
    "analysis": 4,
    "profiles": 3,
    "agents": 4,
    "style": 3,
    "keybindings": 4,
    "docs": 3,
    "default": 3,
}
INSPECTOR_CONTEXT_IDS = tuple(_CONTEXT_CHECK_COUNTS)


class InspectorPanel(QFrame):
    def __init__(
        self,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self._localization = localization
        self._current_screen = "dashboard"
        self._shortcut_screen = "dashboard"
        self._shortcut_value = ""
        self._active_operations: tuple[str, ...] = ()
        self._issue_count = 0

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(10)

        self._title = QLabel()
        self._title.setObjectName("SectionTitle")
        self._status = make_muted_label("")
        self._next = QLabel()
        self._next.setWordWrap(True)
        self._next.setObjectName("CardTitle")
        self._shortcut_title = QLabel()
        self._shortcut_title.setObjectName("CardTitle")
        self._shortcut = make_muted_label("")
        self._checks_title = QLabel()
        self._checks_title.setObjectName("CardTitle")
        self._checks: list[QLabel] = []
        self._risk_title = QLabel()
        self._risk = make_muted_label("")
        self._runtime_title = QLabel()
        self._runtime_title.setObjectName("CardTitle")
        self._runtime = make_muted_label("")
        self._issues = make_muted_label("")

        self._layout.addWidget(self._title)
        self._layout.addWidget(self._status)
        self._layout.addWidget(self._next)
        self._layout.addWidget(self._shortcut_title)
        self._layout.addWidget(self._shortcut)
        self._layout.addWidget(self._checks_title)
        for _ in range(4):
            label = make_muted_label("")
            self._checks.append(label)
            self._layout.addWidget(label)
        self._layout.addWidget(self._risk_title)
        self._layout.addWidget(self._risk)
        self._layout.addWidget(self._runtime_title)
        self._layout.addWidget(self._runtime)
        self._layout.addWidget(self._issues)
        self._layout.addStretch(1)

        if localization is not None:
            localization.language_changed.connect(self._on_language_changed)
        self._render_all()

    def set_context(self, screen: str) -> None:
        self._current_screen = self._context_id(screen)
        self._render_context()

    def set_navigation_shortcut(self, screen: str, shortcut: str) -> None:
        self._shortcut_screen = self._context_id(screen)
        self._shortcut_value = shortcut
        self._render_shortcut()

    def set_runtime_context(
        self,
        active_operations: tuple[str, ...],
        issue_count: int,
    ) -> None:
        self._active_operations = active_operations
        self._issue_count = max(0, issue_count)
        self._render_runtime()

    def _render_all(self) -> None:
        self._shortcut_title.setText(
            self._text("inspector.shortcut.title")
        )
        self._checks_title.setText(
            self._text("inspector.checks.title")
        )
        self._risk_title.setText(self._text("inspector.risk.title"))
        self._runtime_title.setText(
            self._text("inspector.runtime.title")
        )
        self._render_context()
        self._render_shortcut()
        self._render_runtime()

    def _render_context(self) -> None:
        context_id = self._current_screen
        prefix = f"inspector.context.{context_id}"
        self._title.setText(self._text(f"{prefix}.title"))
        self._status.setText(self._text(f"{prefix}.status"))
        self._next.setText(
            self._text(
                "inspector.next_step",
                action=self._text(f"{prefix}.next"),
            )
        )
        check_count = _CONTEXT_CHECK_COUNTS[context_id]
        for index, label in enumerate(self._checks, start=1):
            label.setText(
                f"• {self._text(f'{prefix}.check.{index}')}"
                if index <= check_count
                else ""
            )
        self._risk.setText(self._text(f"{prefix}.risk"))

    def _render_shortcut(self) -> None:
        if not self._shortcut_value:
            self._shortcut.setText(
                self._text("inspector.shortcut.unassigned")
            )
            return
        title = self._text(
            f"inspector.context.{self._shortcut_screen}.title"
        )
        self._shortcut.setText(
            self._text(
                "inspector.shortcut.open",
                shortcut=self._shortcut_value,
                title=title,
            )
        )

    def _render_runtime(self) -> None:
        if self._active_operations:
            visible = "\n".join(
                f"• {item}" for item in self._active_operations[:4]
            )
            remainder = len(self._active_operations) - 4
            if remainder > 0:
                visible += "\n• " + self._text(
                    "inspector.runtime.more",
                    count=remainder,
                )
            self._runtime.setText(visible)
        else:
            self._runtime.setText(self._text("operations.none_active"))
        self._issues.setText(
            self._text("inspector.runtime.no_issues")
            if self._issue_count == 0
            else self._text(
                "inspector.runtime.issues",
                count=self._issue_count,
            )
        )

    def _on_language_changed(self, _locale: str) -> None:
        self._render_all()

    @staticmethod
    def _context_id(screen: str) -> str:
        return screen if screen in _CONTEXT_CHECK_COUNTS else "default"

    def _text(
        self,
        key: str,
        *,
        count: int | None = None,
        **values: object,
    ) -> str:
        return panel_text(
            self._localization,
            key,
            count=count,
            **values,
        )

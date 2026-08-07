from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QWidget,
)

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafety,
)
from persona_training_lab.ui.agents import AgentsScreen
from persona_training_lab.ui.analysis.screen import AnalysisScreen
from persona_training_lab.ui.dashboard.screen import DashboardScreen
from persona_training_lab.ui.datasets.screen import DatasetsScreen
from persona_training_lab.ui.density import screen_density, scaled
from persona_training_lab.ui.docs.screen import DocsScreen
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.keybindings.screen import KeyBindingsScreen
from persona_training_lab.ui.panels.activity_panel import ActivityPanel
from persona_training_lab.ui.panels.inspector_panel import InspectorPanel
from persona_training_lab.ui.panels.issues_panel import IssuesPanel
from persona_training_lab.ui.panels.telemetry_panel import TelemetryPanel
from persona_training_lab.ui.profiles.screen import ProfilesScreen
from persona_training_lab.ui.shell.app_sidebar import NAVIGATION_KEYS, Sidebar
from persona_training_lab.ui.shell.status_bar import AppStatusBar
from persona_training_lab.ui.shell.workspace import WorkspaceStack
from persona_training_lab.ui.snapshots.screen import SnapshotsScreen
from persona_training_lab.ui.style.screen import StyleScreen
from persona_training_lab.ui.tests.screen import TestsScreen
from persona_training_lab.ui.themes.manager import apply_theme
from persona_training_lab.ui.training.screen import TrainingScreen
from persona_training_lab.ui.viewmodels.agents import AgentsViewModel
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel
from persona_training_lab.ui.viewmodels.datasets import DatasetsViewModel
from persona_training_lab.ui.viewmodels.docs import DocsViewModel
from persona_training_lab.ui.viewmodels.profiles import ProfilesViewModel
from persona_training_lab.ui.viewmodels.shell import ShellViewModel
from persona_training_lab.ui.viewmodels.snapshots import SnapshotsViewModel
from persona_training_lab.ui.viewmodels.style import StyleViewModel
from persona_training_lab.ui.viewmodels.telemetry import TelemetryViewModel
from persona_training_lab.ui.viewmodels.tests import TestsViewModel
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


DOCK_TITLE_KEYS: dict[str, str] = {
    "inspector": "dock.inspector",
    "activity": "dock.activity",
    "telemetry": "dock.telemetry",
    "issues": "dock.issues",
}


class MainWindow(QMainWindow):
    def __init__(
        self,
        shell_vm: ShellViewModel,
        dashboard_vm: DashboardViewModel,
        docs_vm: DocsViewModel,
        style_vm: StyleViewModel,
        agents_vm: AgentsViewModel,
        datasets_vm: DatasetsViewModel,
        profiles_vm: ProfilesViewModel,
        training_vm: TrainingViewModel,
        snapshots_vm: SnapshotsViewModel,
        tests_vm: TestsViewModel,
        analysis_vm: AnalysisViewModel,
        telemetry_vm: TelemetryViewModel,
        lineage_runtime_safety: LineageRuntimeSafety | None = None,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._shell_vm = shell_vm
        self._dashboard_vm = dashboard_vm
        self._docs_vm = docs_vm
        self._style_vm = style_vm
        self._agents_vm = agents_vm
        self._datasets_vm = datasets_vm
        self._profiles_vm = profiles_vm
        self._training_vm = training_vm
        self._snapshots_vm = snapshots_vm
        self._tests_vm = tests_vm
        self._analysis_vm = analysis_vm
        self._telemetry_vm = telemetry_vm
        self._lineage_runtime_safety = lineage_runtime_safety
        self._localization = localization or LocalizationManager()
        self._key_binding_manager = KeyBindingManager()
        self._workspace_contexts: dict[str, dict[str, str]] = {}

        self.setWindowTitle("Persona Training Lab")
        self.resize(1600, 1000)
        self.setMinimumSize(1024, 720)

        central = QWidget()
        self.setCentralWidget(central)
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self._workspace = WorkspaceStack()
        self._sidebar = Sidebar(
            style_vm,
            self._go_to_screen,
            self._apply_theme,
        )
        central_layout.addWidget(self._sidebar)
        central_layout.addWidget(self._workspace, 1)

        self._screens: dict[str, QWidget] = {
            "dashboard": DashboardScreen(dashboard_vm),
            "docs": DocsScreen(docs_vm),
            "style": StyleScreen(style_vm, self._apply_theme),
            "agents": AgentsScreen(
                agents_vm,
                self._key_binding_manager,
                lineage_runtime_safety,
            ),
            "datasets": DatasetsScreen(datasets_vm),
            "profiles": ProfilesScreen(profiles_vm),
            "training": TrainingScreen(training_vm),
            "snapshots": SnapshotsScreen(snapshots_vm),
            "tests": TestsScreen(tests_vm),
            "analysis": AnalysisScreen(analysis_vm),
            "keybindings": KeyBindingsScreen(self._key_binding_manager),
        }
        for screen_key, screen in self._screens.items():
            self._workspace.add_screen(screen_key, screen)

        self._status_bar = AppStatusBar(shell_vm)
        self.setStatusBar(self._status_bar)
        self._build_docks()
        self._build_window_menu()
        self._sidebar.set_window_menu(self._window_menu)
        self._apply_localization()
        self._go_to_screen(shell_vm.active_screen or "dashboard")

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(2_000)
        self._status_timer.timeout.connect(self._status_bar.refresh)
        self._status_timer.start()

    def _build_docks(self) -> None:
        self._docks: dict[str, QDockWidget] = {}
        panels = {
            "inspector": InspectorPanel(self._shell_vm),
            "activity": ActivityPanel(self._shell_vm),
            "telemetry": TelemetryPanel(self._telemetry_vm),
            "issues": IssuesPanel(self._shell_vm),
        }
        for key, panel in panels.items():
            dock = QDockWidget(key, self)
            dock.setObjectName(f"{key.title()}Dock")
            dock.setAllowedAreas(
                Qt.DockWidgetArea.LeftDockWidgetArea
                | Qt.DockWidgetArea.RightDockWidgetArea
                | Qt.DockWidgetArea.BottomDockWidgetArea
            )
            dock.setWidget(panel)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
            self._docks[key] = dock

    def _build_window_menu(self) -> None:
        self._window_menu = QMenu(self)
        self._window_actions: dict[str, QAction] = {}
        for key, dock in self._docks.items():
            action = QAction(self)
            action.setCheckable(True)
            action.setChecked(dock.isVisible())
            action.triggered.connect(dock.setVisible)
            dock.visibilityChanged.connect(action.setChecked)
            self._window_menu.addAction(action)
            self._window_actions[key] = action

    def _apply_localization(self) -> None:
        for key, action in self._window_actions.items():
            action.setText(self._localization.text(DOCK_TITLE_KEYS[key]))
        for key, dock in self._docks.items():
            dock.setWindowTitle(self._localization.text(DOCK_TITLE_KEYS[key]))

    def _go_to_screen(self, screen_key: str) -> None:
        if screen_key not in self._screens:
            return
        self._workspace.set_current(screen_key)
        self._sidebar.set_current(screen_key)
        self._shell_vm.active_screen = screen_key

    def _go_to_screen_with_context(
        self,
        screen_key: str,
        context: dict[str, str],
    ) -> None:
        self._workspace_contexts[screen_key] = dict(context)
        screen = self._screens.get(screen_key)
        if screen is not None:
            setter = getattr(screen, "set_lineage_context", None)
            if callable(setter):
                setter(dict(context))
        self._go_to_screen(screen_key)

    def _apply_theme(self, theme: str, accent: str) -> None:
        app = QApplication.instance()
        if app is None:
            return
        apply_theme(app, theme, accent)
        self._sidebar.sync_theme_state()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        agents_screen = self._screens.get("agents")
        if agents_screen is not None:
            close_guard = getattr(agents_screen, "can_close_workspace", None)
            if callable(close_guard) and not close_guard():
                event.ignore()
                return
        super().closeEvent(event)

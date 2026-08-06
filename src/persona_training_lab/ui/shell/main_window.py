from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QDockWidget, QMainWindow, QMenu, QWidget, QHBoxLayout

from persona_training_lab.application.lineage.runtime_safety import (
    LineageRuntimeSafetyService,
)
from persona_training_lab.application.runtime.operations import (
    RuntimeOperationCoordinator,
)
from persona_training_lab.ui.agents import AgentsScreen
from persona_training_lab.ui.analysis.screen import AnalysisScreen
from persona_training_lab.ui.dashboard.screen import DashboardScreen
from persona_training_lab.ui.datasets.screen import DatasetsScreen
from persona_training_lab.ui.density import UiDensity, density_for_screen
from persona_training_lab.ui.docs.screen import DocsScreen
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.keybindings import (
    KeyBindingManager,
    KeyBindingsScreen,
)
from persona_training_lab.ui.panels.activity_panel import ActivityPanel
from persona_training_lab.ui.panels.inspector_panel import InspectorPanel
from persona_training_lab.ui.panels.issues_panel import IssuesPanel
from persona_training_lab.ui.panels.telemetry_panel import TelemetryPanel
from persona_training_lab.ui.profiles.screen import ProfilesScreen
from persona_training_lab.ui.shell.app_sidebar import Sidebar
from persona_training_lab.ui.shell.main_window_context import (
    MainWindowContextMixin,
)
from persona_training_lab.ui.shell.status_bar import AppStatusBar
from persona_training_lab.ui.shell.window_state import WindowStateStore
from persona_training_lab.ui.shell.workspace import WorkspaceStack
from persona_training_lab.ui.snapshots.screen import SnapshotsScreen
from persona_training_lab.ui.style.screen import StyleScreen
from persona_training_lab.ui.tests.screen import TestsScreen
from persona_training_lab.ui.themes.manager import ThemeManager
from persona_training_lab.ui.training.screen import TrainingScreen
from persona_training_lab.ui.viewmodels.agents import AgentsViewModel
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel
from persona_training_lab.ui.viewmodels.datasets import DatasetsViewModel
from persona_training_lab.ui.viewmodels.docs import DocsViewModel
from persona_training_lab.ui.viewmodels.profiles import ProfilesViewModel
from persona_training_lab.ui.viewmodels.snapshots import SnapshotsViewModel
from persona_training_lab.ui.viewmodels.style import StyleViewModel
from persona_training_lab.ui.viewmodels.telemetry import TelemetryViewModel
from persona_training_lab.ui.viewmodels.tests import TestsViewModel
from persona_training_lab.ui.viewmodels.training import TrainingViewModel


DOCK_TITLE_KEYS = {
    "inspector": "dock.inspector",
    "activity": "dock.activity",
    "telemetry": "dock.telemetry",
    "issues": "dock.issues",
}


class MainWindow(MainWindowContextMixin, QMainWindow):
    def __init__(
        self,
        *,
        dashboard_vm: DashboardViewModel,
        agents_vm: AgentsViewModel,
        profiles_vm: ProfilesViewModel,
        datasets_vm: DatasetsViewModel,
        training_vm: TrainingViewModel,
        snapshots_vm: SnapshotsViewModel,
        tests_vm: TestsViewModel,
        analysis_vm: AnalysisViewModel,
        style_vm: StyleViewModel,
        docs_vm: DocsViewModel,
        telemetry_vm: TelemetryViewModel,
        on_shutdown: Callable[[], None],
        localization: LocalizationManager,
        runtime_operations: RuntimeOperationCoordinator | None = None,
        lineage_runtime_safety: LineageRuntimeSafetyService | None = None,
        theme_manager: ThemeManager | None = None,
        initial_density: UiDensity | None = None,
        window_state_store: WindowStateStore | None = None,
    ) -> None:
        super().__init__()
        self._on_shutdown = on_shutdown
        self._localization = localization
        self._runtime_operations = runtime_operations
        self._telemetry_vm = telemetry_vm
        self._theme_manager = theme_manager or ThemeManager()
        self._window_state = window_state_store or WindowStateStore()
        self._density = initial_density or density_for_screen(
            self.screen().availableGeometry().height()
            if self.screen() is not None
            else 900
        )
        self._settings_menu: QMenu | None = None
        self._dock_menu: QMenu | None = None
        self._workspace_restore_attempted = False
        self._workspace_restored = False
        self._dock_restore_barrier_active = True

        self.setWindowTitle(localization.text("app.title"))
        self.setObjectName("PersonaTrainingLabMainWindow")
        icon_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / "brand" / "main.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(
            self._density.window_width,
            self._density.window_height,
        )
        self.setMinimumSize(
            920,
            580,
        )

        prefs = style_vm.load()
        self._current_theme = prefs.get("theme") or "velvet"
        self._current_accent = prefs.get("accent_palette") or "cyan"

        root = QWidget()
        body = QHBoxLayout(root)
        body.setContentsMargins(
            self._density.root_margin,
            self._density.root_margin,
            self._density.root_margin,
            self._density.root_margin,
        )
        body.setSpacing(self._density.root_spacing)

        self._sidebar = Sidebar(
            style_vm=style_vm,
            on_apply_theme=self._apply_style,
            active_workflows=[],
            localization=localization,
        )
        self._key_binding_manager = KeyBindingManager(parent=self)
        self._workspace = WorkspaceStack()
        self._workspace.register(
            "dashboard",
            DashboardScreen(dashboard_vm, localization),
        )
        self._workspace.register(
            "profiles",
            ProfilesScreen(profiles_vm, localization),
        )
        self._workspace.register(
            "agents",
            AgentsScreen(
                agents_vm,
                self._key_binding_manager,
                lineage_runtime_safety,
            ),
        )
        self._workspace.register(
            "datasets",
            DatasetsScreen(datasets_vm, localization),
        )
        self._workspace.register(
            "training",
            TrainingScreen(training_vm, localization),
        )
        self._workspace.register(
            "snapshots",
            SnapshotsScreen(snapshots_vm),
        )
        tests_screen = TestsScreen(tests_vm)
        tests_screen.open_analysis_requested.connect(
            lambda: self._go_to_screen("analysis")
        )
        self._workspace.register("tests", tests_screen)
        self._workspace.register(
            "analysis",
            AnalysisScreen(analysis_vm),
        )
        self._workspace.register(
            "style",
            StyleScreen(style_vm, self._apply_style),
        )
        self._workspace.register(
            "keybindings",
            KeyBindingsScreen(self._key_binding_manager),
        )
        self._workspace.register("docs", DocsScreen(docs_vm))

        body.addWidget(self._sidebar)
        body.addWidget(self._workspace, 1)
        self.setCentralWidget(root)

        self._sidebar.screen_selected.connect(self._on_screen_selected)

        self._status = AppStatusBar(localization)
        self.setStatusBar(self._status)
        self._status.set_message_key("status.ready")
        self._status.set_style_message(
            f"{self._current_theme.title()} · "
            f"{self._current_accent.title()} · {self._density.name}"
        )

        self._docks: dict[str, QDockWidget] = {}
        self._inspector_panel = InspectorPanel(localization)
        inspector = self._register_dock(
            "inspector",
            self._inspector_panel,
            Qt.DockWidgetArea.RightDockWidgetArea,
        )
        activity = self._register_dock(
            "activity",
            ActivityPanel(localization),
            Qt.DockWidgetArea.BottomDockWidgetArea,
        )
        telemetry = self._register_dock(
            "telemetry",
            TelemetryPanel(telemetry_vm, localization),
            Qt.DockWidgetArea.BottomDockWidgetArea,
        )
        issues = self._register_dock(
            "issues",
            IssuesPanel(localization),
            Qt.DockWidgetArea.BottomDockWidgetArea,
        )
        self._workspace_docks = (inspector, activity, telemetry, issues)
        self.tabifyDockWidget(activity, telemetry)
        self.tabifyDockWidget(telemetry, issues)
        activity.raise_()

        self._build_settings_menu()
        self._refresh_shell_language()
        localization.language_changed.connect(self._refresh_shell_language)
        self._restore_window_state()
        QTimer.singleShot(0, self._finish_dock_restore_barrier)

    def _register_dock(
        self,
        dock_id: str,
        widget: QWidget,
        area: Qt.DockWidgetArea,
    ) -> QDockWidget:
        dock = QDockWidget(self)
        dock.setObjectName(f"ptl.dock.{dock_id}")
        dock.setWidget(widget)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(area, dock)
        self._docks[dock_id] = dock
        return dock

    def _build_settings_menu(self) -> None:
        self._settings_menu = self.menuBar().addMenu("")
        self._dock_menu = self._settings_menu.addMenu("")
        for dock_id, dock in self._docks.items():
            action = dock.toggleViewAction()
            action.setData(dock_id)
            self._dock_menu.addAction(action)

    def _refresh_shell_language(self, _locale: str = "") -> None:
        self.setWindowTitle(self._localization.text("app.title"))
        if self._settings_menu is not None:
            self._settings_menu.setTitle(
                self._localization.text("shell.settings")
            )
        if self._dock_menu is not None:
            self._dock_menu.setTitle(
                self._localization.text("shell.panels")
            )
        for dock_id, dock in self._docks.items():
            title = self._localization.text(DOCK_TITLE_KEYS[dock_id])
            dock.setWindowTitle(title)
            dock.toggleViewAction().setText(title)
        current_screen = self._workspace.current_key()
        if current_screen:
            self._status.set_message_key(
                "status.current_workspace",
                screen=self._screen_title(current_screen),
            )

    def _text(self, key: str, **values: Any) -> str:
        return self._localization.text(key, **values)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._persist_window_state()
        self._on_shutdown()
        super().closeEvent(event)

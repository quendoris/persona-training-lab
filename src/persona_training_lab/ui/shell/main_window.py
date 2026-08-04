from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QDockWidget, QFrame, QHBoxLayout, QLabel, QMainWindow, QMenu, QVBoxLayout, QWidget

from persona_training_lab.ui.components.panels import make_muted_label, make_status_label
from persona_training_lab.ui.agents.screen import AgentsScreen
from persona_training_lab.ui.dashboard.screen import DashboardScreen
from persona_training_lab.ui.datasets.screen import DatasetsScreen
from persona_training_lab.ui.docs.screen import DocsScreen
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.keybindings.screen import KeyBindingsScreen
from persona_training_lab.ui.panels.activity_panel import ActivityPanel
from persona_training_lab.ui.panels.inspector_panel import InspectorPanel
from persona_training_lab.ui.panels.issues_panel import IssuesPanel
from persona_training_lab.ui.panels.telemetry_panel import TelemetryPanel
from persona_training_lab.ui.profiles.screen import ProfilesScreen
from persona_training_lab.ui.shell.app_sidebar import Sidebar
from persona_training_lab.ui.shell.status_bar import AppStatusBar
from persona_training_lab.ui.shell.workspace import WorkspaceStack
from persona_training_lab.ui.style.screen import StyleScreen
from persona_training_lab.ui.training.screen import TrainingScreen
from persona_training_lab.ui.snapshots.screen import SnapshotsScreen
from persona_training_lab.ui.tests.screen import TestsScreen
from persona_training_lab.ui.analysis.screen import AnalysisScreen
from persona_training_lab.ui.density import screen_density, scaled
from persona_training_lab.ui.themes.manager import apply_theme
from persona_training_lab.ui.viewmodels.dashboard import DashboardViewModel
from persona_training_lab.ui.viewmodels.datasets import DatasetsViewModel
from persona_training_lab.ui.viewmodels.docs import DocsViewModel
from persona_training_lab.ui.viewmodels.agents import AgentsViewModel
from persona_training_lab.ui.viewmodels.profiles import ProfilesViewModel
from persona_training_lab.ui.viewmodels.shell import ShellViewModel
from persona_training_lab.ui.viewmodels.style import StyleViewModel
from persona_training_lab.ui.viewmodels.training import TrainingViewModel
from persona_training_lab.ui.viewmodels.snapshots import SnapshotsViewModel
from persona_training_lab.ui.viewmodels.tests import TestsViewModel
from persona_training_lab.ui.viewmodels.analysis import AnalysisViewModel
from persona_training_lab.ui.viewmodels.telemetry import TelemetryViewModel


class _PlaceholderScreen(QWidget):
    def __init__(self, title_text: str, subtitle_text: str, helper_text: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(scaled(22), scaled(18), scaled(22), scaled(18))
        header_layout.setSpacing(scaled(8))
        title = QLabel(title_text)
        title.setObjectName("ScreenTitle")
        subtitle = make_muted_label(subtitle_text)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        card = QFrame()
        card.setObjectName("AccentCard")
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel("Модуль в работе"))
        card_layout.addWidget(make_muted_label(helper_text))
        badges = QHBoxLayout()
        badges.addWidget(make_status_label("Phase 2.1"))
        badges.addWidget(make_status_label("скоро оживим", warning=True))
        badges.addStretch(1)
        card_layout.addLayout(badges)
        layout.addWidget(card)
        layout.addStretch(1)


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
    ) -> None:
        super().__init__()
        self._shell_vm = shell_vm
        self._style_vm = style_vm
        self._density = screen_density()
        self.setWindowTitle(shell_vm.title)
        self.resize(self._density.window_width, self._density.window_height)
        self.setMinimumSize(scaled(960, minimum=920), scaled(620, minimum=580))

        prefs = style_vm.load()
        self._current_theme = prefs.get("theme") or "velvet"
        self._current_accent = prefs.get("accent_palette") or "cyan"

        root = QWidget()
        body = QHBoxLayout(root)
        body.setContentsMargins(self._density.root_margin, self._density.root_margin, self._density.root_margin, self._density.root_margin)
        body.setSpacing(self._density.root_spacing)

        self._sidebar = Sidebar(
            style_vm=style_vm,
            on_apply_theme=self._apply_style,
            active_workflows=["Training · trn_014", "Evaluation · evr_004"],
        )
        self._key_binding_manager = KeyBindingManager(parent=self)
        self._workspace = WorkspaceStack()
        self._workspace.register("dashboard", DashboardScreen(dashboard_vm))
        self._workspace.register("profiles", ProfilesScreen(profiles_vm))
        self._workspace.register("agents", AgentsScreen(agents_vm, self._key_binding_manager))
        self._workspace.register("datasets", DatasetsScreen(datasets_vm))
        self._workspace.register("training", TrainingScreen(training_vm))
        self._workspace.register("snapshots", SnapshotsScreen(snapshots_vm))
        tests_screen = TestsScreen(tests_vm)
        tests_screen.open_analysis_requested.connect(lambda: self._go_to_screen("analysis"))
        self._workspace.register("tests", tests_screen)
        self._workspace.register("analysis", AnalysisScreen(analysis_vm))
        self._workspace.register("style", StyleScreen(style_vm, self._apply_style))
        self._workspace.register("keybindings", KeyBindingsScreen(self._key_binding_manager))
        self._workspace.register("docs", DocsScreen(docs_vm))

        body.addWidget(self._sidebar)
        body.addWidget(self._workspace, 1)
        self.setCentralWidget(root)

        self._sidebar.screen_selected.connect(self._on_screen_selected)

        self._status = AppStatusBar()
        self.setStatusBar(self._status)
        self._status.set_message(shell_vm.status_message)
        self._status.set_style_message(f"{self._current_theme.title()} · {self._current_accent.title()} · {self._density.name}")

        self._docks: dict[str, QDockWidget] = {}
        self._inspector_panel = InspectorPanel()
        inspector = self._register_dock("Инспектор", self._inspector_panel, Qt.RightDockWidgetArea)
        activity = self._register_dock("Активность", ActivityPanel(), Qt.BottomDockWidgetArea)
        telemetry = self._register_dock("Телеметрия", TelemetryPanel(telemetry_vm), Qt.BottomDockWidgetArea)
        issues = self._register_dock("Проблемы", IssuesPanel(), Qt.BottomDockWidgetArea)
        self.tabifyDockWidget(activity, telemetry)
        self.tabifyDockWidget(telemetry, issues)
        inspector.raise_()
        telemetry.raise_()

        windows_menu = self._build_windows_menu()
        self._sidebar.set_window_menu(windows_menu)
        self.menuBar().hide()
        self._inspector_panel.set_context("dashboard")
        self._schedule_rebalance()

    def _register_dock(self, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setObjectName(title)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(area, dock)
        dock.topLevelChanged.connect(lambda _floating, _dock=dock: self._schedule_rebalance())
        dock.visibilityChanged.connect(lambda _visible, _dock=dock: self._schedule_rebalance())
        self._docks[title] = dock
        return dock

    def _schedule_rebalance(self) -> None:
        QTimer.singleShot(0, self._rebalance_docks)

    def _rebalance_docks(self) -> None:
        right = [dock for dock in self._docks.values() if dock.isVisible() and not dock.isFloating() and self.dockWidgetArea(dock) == Qt.RightDockWidgetArea]
        bottom = [dock for dock in self._docks.values() if dock.isVisible() and not dock.isFloating() and self.dockWidgetArea(dock) == Qt.BottomDockWidgetArea]
        if right:
            self.resizeDocks(right, [self._density.right_dock_width for _ in right], Qt.Horizontal)
        if bottom:
            self.resizeDocks(bottom, [self._density.bottom_dock_height for _ in bottom], Qt.Vertical)
        if self.centralWidget() is not None:
            self.centralWidget().updateGeometry()

    def _build_windows_menu(self) -> QMenu:
        menu = QMenu("Панели", self)
        for title in ["Инспектор", "Активность", "Телеметрия", "Проблемы"]:
            dock = self._docks[title]
            action = dock.toggleViewAction()
            action.setText(f"Показать / скрыть: {title}")
            menu.addAction(action)
        return menu

    def _go_to_screen(self, screen: str) -> None:
        self._sidebar.set_current(screen)
        self._on_screen_selected(screen)

    def _on_screen_selected(self, screen: str) -> None:
        previous = self._workspace.current_workspace_key()
        if not self._workspace.show_workspace(screen):
            if previous:
                self._sidebar.set_current(previous)
            return
        self._shell_vm.navigate(screen)
        self._inspector_panel.set_context(screen)
        self._status.set_message(f"Текущее пространство: {screen}")

    def _apply_style(self, theme_name: str, accent_name: str) -> None:
        app = QApplication.instance()
        if app is None:
            return
        self._current_theme = theme_name
        self._current_accent = accent_name
        apply_theme(app, theme_name, accent_name)
        self._status.set_style_message(f"{theme_name.title()} · {accent_name.title()} · {self._density.name}")

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        if not self._workspace.request_current_leave():
            event.ignore()
            return
        super().closeEvent(event)

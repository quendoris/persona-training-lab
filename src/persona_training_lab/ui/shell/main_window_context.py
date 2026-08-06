from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QCloseEvent, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QPushButton,
    QWidget,
)

from persona_training_lab.application.operations_center import OperationsCenterService
from persona_training_lab.ui.shell.main_window import MainWindow as _MainWindow
from persona_training_lab.ui.shell.window_state import WindowStateStore


TAB_SHORTCUTS: tuple[tuple[str, str], ...] = (
    ("nav_dashboard", "dashboard"),
    ("nav_profiles", "profiles"),
    ("nav_agents", "agents"),
    ("nav_datasets", "datasets"),
    ("nav_training", "training"),
    ("nav_snapshots", "snapshots"),
    ("nav_tests", "tests"),
    ("nav_analysis", "analysis"),
    ("nav_style", "style"),
    ("nav_docs", "docs"),
    ("nav_keybindings", "keybindings"),
)


class MainWindow(_MainWindow):
    """Context navigation, live operations center and durable shell state."""

    def __init__(
        self,
        *args,
        operations_center: OperationsCenterService | None = None,
        **kwargs,
    ) -> None:
        self._operations_center = operations_center
        self._tab_shortcuts: list[QShortcut] = []
        self._guidance_generation = 0
        self._guidance_target: QWidget | None = None
        self._window_state_store = WindowStateStore()
        self._suspend_dock_rebalance = True
        self._restored_dock_state = False
        super().__init__(*args, **kwargs)

        restored = self._window_state_store.restore(self)
        self._restored_dock_state = restored.docks_restored
        QTimer.singleShot(0, self._finish_initial_dock_layout)

        self._connect_operations_center()
        self._connect_dashboard_navigation()
        self._key_binding_manager.bindings_changed.connect(
            self._sync_tab_shortcuts
        )
        self._sync_tab_shortcuts()

        self._operations_timer = QTimer(self)
        self._operations_timer.setInterval(900)
        self._operations_timer.timeout.connect(self._refresh_operations_chrome)
        self._operations_timer.start()

        if (
            restored.workspace_key
            and self._workspace.workspace(restored.workspace_key) is not None
        ):
            self._go_to_screen(restored.workspace_key)
        else:
            self._refresh_operations_chrome()

    def _go_to_screen_with_context(
        self,
        screen: str,
        context: dict[str, object],
    ) -> None:
        target = self._workspace.workspace(screen)
        if target is not None:
            setter = getattr(target, "set_lineage_context", None)
            if callable(setter):
                setter(context)
            else:
                view_model = getattr(target, "_vm", None)
                vm_setter = getattr(view_model, "set_lineage_context", None)
                if callable(vm_setter):
                    vm_setter(context)
                    refresher = getattr(target, "_refresh_all", None)
                    if callable(refresher):
                        refresher()
        self._go_to_screen(screen)

    def _connect_operations_center(self) -> None:
        service = self._operations_center
        if service is None:
            return
        for dock_id in ("activity", "issues"):
            dock = self._docks.get(dock_id)
            panel = dock.widget() if dock is not None else None
            setter = getattr(panel, "set_service", None)
            if callable(setter):
                setter(service)
            signal = getattr(panel, "navigate_requested", None)
            if signal is not None:
                signal.connect(self._navigate_with_guidance)

    def _connect_dashboard_navigation(self) -> None:
        dashboard = self._workspace.workspace("dashboard")
        signal = getattr(dashboard, "navigate_requested", None)
        if signal is not None:
            signal.connect(self._navigate_with_guidance)

    def _sync_tab_shortcuts(self) -> None:
        for shortcut in self._tab_shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self._tab_shortcuts.clear()

        for binding_id, screen in TAB_SHORTCUTS:
            sequence_text = self._key_binding_manager.sequence(binding_id)
            shortcut = QShortcut(QKeySequence(sequence_text), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(
                lambda screen=screen: self._go_to_screen(screen)
            )
            self._tab_shortcuts.append(shortcut)
            hint = getattr(self._sidebar, "set_navigation_shortcut_hint", None)
            if callable(hint):
                hint(screen, sequence_text)

        self._sync_inspector_shortcut(
            self._workspace.current_workspace_key() or "dashboard"
        )

    def _navigate_with_guidance(self, screen: str, focus_text: str = "") -> None:
        self._go_to_screen(screen)
        if focus_text:
            QTimer.singleShot(
                0,
                lambda: self._pulse_guidance_target(screen, focus_text),
            )

    def _pulse_guidance_target(self, screen: str, focus_text: str) -> None:
        workspace = self._workspace.workspace(screen)
        if workspace is None:
            return
        target = self._find_guidance_target(workspace, focus_text)
        if target is None:
            self._status.set_message_key(
                "status.opened_with_focus",
                title=self._screen_title(screen),
                focus=focus_text,
            )
            return

        self._clear_guidance_effect()
        self._guidance_generation += 1
        generation = self._guidance_generation
        self._guidance_target = target
        effect = QGraphicsDropShadowEffect(target)
        accent = target.palette().color(QPalette.ColorRole.Highlight)
        if not accent.isValid():
            accent = QColor("#22D3EE")
        effect.setColor(accent)
        effect.setOffset(0, 0)
        effect.setBlurRadius(26)
        target.setGraphicsEffect(effect)
        target.setFocus(Qt.FocusReason.ShortcutFocusReason)

        def pulse(step: int = 0) -> None:
            if generation != self._guidance_generation:
                return
            if step >= 8:
                self._clear_guidance_effect(target)
                return
            try:
                effect.setBlurRadius(10 if step % 2 else 28)
            except RuntimeError:
                self._guidance_target = None
                return
            QTimer.singleShot(180, lambda: pulse(step + 1))

        pulse()

    def _clear_guidance_effect(self, expected: QWidget | None = None) -> None:
        target = self._guidance_target
        if target is None or (expected is not None and target is not expected):
            return
        self._guidance_target = None
        try:
            target.setGraphicsEffect(None)
        except RuntimeError:
            return

    @staticmethod
    def _find_guidance_target(
        workspace: QWidget,
        focus_text: str,
    ) -> QWidget | None:
        needle = " ".join(focus_text.casefold().split())
        buttons = [
            button
            for button in workspace.findChildren(QPushButton)
            if button.isVisible() and button.isEnabled()
        ]
        for button in buttons:
            haystack = " ".join(
                f"{button.text()} {button.toolTip()}".casefold().split()
            )
            if needle and needle in haystack:
                return button
        if buttons:
            return buttons[0]
        for frame in workspace.findChildren(QFrame):
            if not frame.isVisible():
                continue
            if frame.objectName() in {"ActionCard", "WarningBlock"}:
                return frame
        return None

    def _sync_inspector_shortcut(self, screen: str) -> None:
        setter = getattr(
            self._inspector_panel,
            "set_navigation_shortcut",
            None,
        )
        if not callable(setter):
            return
        for binding_id, target_screen in TAB_SHORTCUTS:
            if target_screen != screen:
                continue
            setter(screen, self._key_binding_manager.sequence(binding_id))
            return
        setter(screen, "")

    def _refresh_operations_chrome(self) -> None:
        service = self._operations_center
        if service is None:
            return
        active = service.active_items()
        setter = getattr(self._sidebar, "set_active_workflows", None)
        if callable(setter):
            setter(
                tuple(
                    f"{item.title} · {item.status}"
                    for item in active[:6]
                )
            )
        issues = service.issue_items(100)
        inspector_setter = getattr(
            self._inspector_panel,
            "set_runtime_context",
            None,
        )
        if callable(inspector_setter):
            inspector_setter(
                tuple(item.title for item in active),
                len(issues),
            )

    def _rebalance_docks(self) -> None:
        if self._suspend_dock_rebalance:
            return
        super()._rebalance_docks()

    def _finish_initial_dock_layout(self) -> None:
        self._suspend_dock_rebalance = False
        if self._restored_dock_state:
            central = self.centralWidget()
            if central is not None:
                central.updateGeometry()
            return
        super()._rebalance_docks()

    def _on_screen_selected(self, screen: str) -> None:
        super()._on_screen_selected(screen)
        self._sync_inspector_shortcut(screen)
        self._refresh_operations_chrome()

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        super().closeEvent(event)
        if not event.isAccepted():
            return

        self._operations_timer.stop()
        self._clear_guidance_effect()
        self._window_state_store.save(
            self,
            self._workspace.current_workspace_key(),
        )

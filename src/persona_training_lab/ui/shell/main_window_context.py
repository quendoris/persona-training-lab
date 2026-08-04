from __future__ import annotations

from persona_training_lab.ui.shell.main_window import MainWindow as _MainWindow


class MainWindow(_MainWindow):
    """Main window with explicit context transfer between workspaces."""

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

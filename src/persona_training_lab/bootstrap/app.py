from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from persona_training_lab.bootstrap.wiring import build_container
from persona_training_lab.ui.density import apply_density, apply_scaled_styles
from persona_training_lab.ui.shell.main_window import MainWindow
from persona_training_lab.ui.themes.manager import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    container = build_container()
    prefs = container.style_vm.load()
    density = apply_density(app, prefs.get("ui_scale"))
    apply_theme(app, prefs.get("theme"), prefs.get("accent_palette"))
    apply_scaled_styles(app, density.scale, immediate=True)

    window = MainWindow(
        shell_vm=container.shell_vm,
        dashboard_vm=container.dashboard_vm,
        docs_vm=container.docs_vm,
        style_vm=container.style_vm,
        agents_vm=container.agents_vm,
        datasets_vm=container.datasets_vm,
        profiles_vm=container.profiles_vm,
        training_vm=container.training_vm,
        snapshots_vm=container.snapshots_vm,
        tests_vm=container.tests_vm,
        analysis_vm=container.analysis_vm,
        telemetry_vm=container.telemetry_vm,
    )
    window.setProperty("ptl_density_name", density.name)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
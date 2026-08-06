from __future__ import annotations

import sys
import threading

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

from persona_training_lab import __version__
from persona_training_lab.bootstrap.wiring import build_container
from persona_training_lab.ui.density import (
    apply_density,
    apply_scaled_styles,
)
from persona_training_lab.ui.safe_application import SafeApplication
from persona_training_lab.ui.shell.main_window_context import MainWindow
from persona_training_lab.ui.themes.manager import apply_theme


_QT_MESSAGE_HANDLER = None


def main() -> int:
    app = SafeApplication(sys.argv)
    app.setOrganizationName("Persona Training Lab")
    app.setOrganizationDomain("persona-training-lab.local")
    app.setApplicationName("Persona Training Lab")
    app.setApplicationVersion(__version__)

    container = build_container()
    app.set_error_reporter(container.error_reporter)
    _install_exception_boundaries(container.error_reporter)
    _install_qt_message_boundary(container.error_reporter)

    prefs = container.style_vm.load()
    density = apply_density(app, prefs.get("ui_scale"))
    apply_theme(
        app,
        prefs.get("theme"),
        prefs.get("accent_palette"),
    )
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
        lineage_runtime_safety=container.lineage_runtime_safety,
        operations_center=container.operations_center,
    )
    window.setProperty("ptl_density_name", density.name)
    window.show()
    return app.exec()


def _install_exception_boundaries(error_reporter) -> None:
    def handle_exception(exc_type, exc, traceback_object) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, traceback_object)
            return
        exc.__traceback__ = traceback_object
        error_reporter.capture(
            exc,
            component="python.main_thread",
            user_message=(
                "Фоновая операция завершилась с ошибкой, но приложение "
                "осталось доступно."
            ),
            entity_kind="python",
            entity_id="main_thread",
        )

    def handle_thread_exception(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is SystemExit:
            return
        error = args.exc_value or RuntimeError(
            f"Thread failed with {args.exc_type.__name__}"
        )
        error.__traceback__ = args.exc_traceback
        error_reporter.capture(
            error,
            component="python.worker_thread",
            user_message=(
                "Фоновая задача остановлена безопасно; интерфейс продолжает "
                "работать."
            ),
            entity_kind="thread",
            entity_id=(
                args.thread.name
                if args.thread is not None
                else "unknown"
            ),
        )

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception


def _install_qt_message_boundary(error_reporter):
    """Route Qt diagnostics into throttled logs instead of stderr spam."""

    levels = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "ERROR",
        QtMsgType.QtFatalMsg: "CRITICAL",
    }

    def handle_qt_message(message_type, context, message) -> None:
        level = levels.get(message_type, "WARNING")
        if level == "DEBUG":
            return
        error_reporter.report_message(
            str(message),
            component="qt.message",
            level=level,
            entity_kind="qt",
            entity_id=getattr(context, "category", "") or "runtime",
            context={
                "file": getattr(context, "file", "") or "",
                "line": getattr(context, "line", 0) or 0,
                "function": getattr(context, "function", "") or "",
                "category": getattr(context, "category", "") or "",
                "qt_message_type": str(message_type),
            },
        )

    global _QT_MESSAGE_HANDLER
    _QT_MESSAGE_HANDLER = handle_qt_message
    qInstallMessageHandler(handle_qt_message)
    return handle_qt_message


if __name__ == "__main__":
    raise SystemExit(main())

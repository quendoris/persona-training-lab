from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDockWidget, QWidget

from persona_training_lab import __version__
from persona_training_lab.bootstrap.wiring import build_container
from persona_training_lab.ui.density import apply_density, apply_scaled_styles
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.safe_application import SafeApplication
from persona_training_lab.ui.shell.app_sidebar import NAVIGATION_KEYS
from persona_training_lab.ui.shell.main_window_background import MainWindow
from persona_training_lab.ui.themes.manager import apply_theme


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "visual-audit"
DEFAULT_WIDTH = 0
DEFAULT_HEIGHT = 0
DEFAULT_SCALE = "0.90"
DEFAULT_THEME = "velvet"
DEFAULT_ACCENT = "cyan"
DEFAULT_SETTLE_MS = 250
DEFAULT_CAPTURE_HOTKEY = "F12"


def _git(*args: str) -> str:
    try:
        completed = subprocess.run(
            ("git", *args),
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _settle(milliseconds: int) -> None:
    app = SafeApplication.instance()
    if app is None:
        return
    app.processEvents()
    if milliseconds <= 0:
        return
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()
    app.processEvents()


def _build_window(
    *,
    scale: str,
    theme: str,
    accent: str,
    initial_locale: str,
) -> tuple[SafeApplication, MainWindow, LocalizationManager]:
    app = SafeApplication(sys.argv[:1])
    app.setOrganizationName("Persona Training Lab")
    app.setOrganizationDomain("persona-training-lab.local")
    app.setApplicationName("Persona Training Lab Visual Audit")
    app.setApplicationVersion(__version__)

    container = build_container()
    app.set_error_reporter(container.error_reporter)
    container.style_vm.save(theme, accent, "soft_glow")
    container.style_vm.save_ui_scale(scale)
    container.style_vm.save_language(initial_locale)

    prefs = container.style_vm.load()
    localization = LocalizationManager(
        app,
        initial_locale=initial_locale,
        persist_locale=container.style_vm.save_language,
    )
    density = apply_density(app, prefs.get("ui_scale"))
    apply_theme(
        app,
        prefs.get("theme") or theme,
        prefs.get("accent_palette") or accent,
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
        localization=localization,
    )
    app.aboutToQuit.connect(window.shutdown_background_work)
    window.setProperty("ptl_density_name", density.name)
    return app, window, localization


def _capture_widget(widget: QWidget, target: Path) -> dict[str, object]:
    pixmap = widget.grab()
    if pixmap.isNull():
        raise RuntimeError(f"Qt returned a null pixmap for {target.name}")
    if not pixmap.save(str(target), "PNG"):
        raise RuntimeError(f"Qt could not save {target}")

    geometry = widget.frameGeometry()
    screen = widget.screen()
    return {
        "file": str(target),
        "class": type(widget).__name__,
        "object_name": widget.objectName(),
        "window_title": widget.windowTitle(),
        "x": geometry.x(),
        "y": geometry.y(),
        "width": geometry.width(),
        "height": geometry.height(),
        "active": widget.isActiveWindow(),
        "floating": isinstance(widget, QDockWidget) and widget.isFloating(),
        "screen": screen.name() if screen is not None else "",
        "device_pixel_ratio": pixmap.devicePixelRatio(),
    }


def _capture_window(window: MainWindow, target: Path) -> None:
    _capture_widget(window, target)


def _write_bundle(session_dir: Path, manifest: dict[str, object]) -> Path:
    manifest_path = session_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    captures = manifest.get("captures")
    failures = manifest.get("failures")
    routes = manifest.get("routes")
    locales = manifest.get("locales")
    summary_lines = [
        "Persona Training Lab visual audit",
        f"Mode: {manifest.get('mode', 'automatic')}",
        f"Commit: {manifest['commit']}",
        f"Branch: {manifest['branch']}",
        f"Routes: {len(routes) if isinstance(routes, list) else 0}",
        "Locales: " + ", ".join(locales if isinstance(locales, list) else []),
        f"Captures: {len(captures) if isinstance(captures, list) else 0}",
        f"Failures: {len(failures) if isinstance(failures, list) else 0}",
    ]
    (session_dir / "summary.txt").write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    bundle = session_dir / "visual-audit.zip"
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(session_dir.rglob("*")):
            if path.is_file() and path != bundle:
                archive.write(path, path.relative_to(session_dir))
    return bundle


def _new_manifest(
    *,
    mode: str,
    commit: str,
    branch: str,
    dirty: bool,
    routes: Iterable[str],
    locales: Iterable[str],
    width: int,
    height: int,
    scale: str,
    theme: str,
    accent: str,
    settle_ms: int,
) -> dict[str, object]:
    window_geometry: dict[str, object]
    if width > 0 and height > 0:
        window_geometry = {"width": width, "height": height}
    else:
        window_geometry = {"mode": "maximized"}
    return {
        "schema": "ptl:visual-audit:v1",
        "mode": mode,
        "commit": commit,
        "branch": branch,
        "dirty": dirty,
        "captured_at": datetime.now(UTC).isoformat(),
        "routes": list(routes),
        "locales": list(locales),
        "window": window_geometry,
        "ui_scale": scale,
        "theme": theme,
        "accent": accent,
        "qt_qpa_platform": os.environ.get("QT_QPA_PLATFORM", ""),
        "settle_ms": settle_ms,
        "captures": [],
        "failures": [],
    }


def _session_directory(output_root: Path, commit: str, suffix: str = "") -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = f"{stamp}-{commit[:12]}"
    if suffix:
        name += f"-{suffix}"
    session_dir = output_root.resolve() / name
    session_dir.mkdir(parents=True, exist_ok=False)
    return session_dir


def _shutdown_window(app: SafeApplication | None, window: MainWindow | None) -> None:
    if window is not None:
        window.shutdown_background_work()
        window.close()
    if app is not None:
        app.processEvents()


def _stabilize_window_geometry(
    window: MainWindow,
    *,
    width: int,
    height: int,
    settle_ms: int,
) -> None:
    if width <= 0 or height <= 0:
        window.showMaximized()
        _settle(settle_ms)
        return

    expected = (width, height)
    window.resize(width, height)
    _settle(settle_ms)
    actual = (window.width(), window.height())
    if actual != expected:
        window.resize(width, height)
        _settle(0)
        actual = (window.width(), window.height())
    if actual != expected:
        raise RuntimeError(
            "Automatic visual-audit geometry drift: "
            f"expected={width}x{height}, actual={actual[0]}x{actual[1]}"
        )


def run_visual_audit(
    *,
    output_root: Path,
    locales: Iterable[str],
    width: int,
    height: int,
    scale: str,
    theme: str,
    accent: str,
    settle_ms: int,
) -> Path:
    locale_list = tuple(dict.fromkeys(locales))
    if not locale_list:
        raise ValueError("At least one locale is required")

    commit = _git("rev-parse", "HEAD")
    branch = _git("branch", "--show-current")
    status = _git("status", "--porcelain")
    session_dir = _session_directory(output_root, commit)
    capture_dir = session_dir / "screenshots"
    capture_dir.mkdir()

    routes = tuple(NAVIGATION_KEYS)
    manifest = _new_manifest(
        mode="automatic",
        commit=commit,
        branch=branch,
        dirty=status not in {"", "unknown"},
        routes=routes,
        locales=locale_list,
        width=width,
        height=height,
        scale=scale,
        theme=theme,
        accent=accent,
        settle_ms=settle_ms,
    )

    previous_cwd = Path.cwd()
    app: SafeApplication | None = None
    window: MainWindow | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="ptl-visual-audit-") as workspace:
            os.chdir(workspace)
            try:
                app, window, localization = _build_window(
                    scale=scale,
                    theme=theme,
                    accent=accent,
                    initial_locale=locale_list[0],
                )
                available = set(localization.available_locales())
                unknown = [locale for locale in locale_list if locale not in available]
                if unknown:
                    raise RuntimeError(
                        "Unsupported visual-audit locales: " + ", ".join(unknown)
                    )

                window.show()
                _stabilize_window_geometry(
                    window,
                    width=width,
                    height=height,
                    settle_ms=settle_ms,
                )

                captures = manifest["captures"]
                assert isinstance(captures, list)
                for locale in locale_list:
                    localization.set_locale(locale, persist=False)
                    _stabilize_window_geometry(
                        window,
                        width=width,
                        height=height,
                        settle_ms=settle_ms,
                    )
                    for route in routes:
                        window._go_to_screen(route)
                        _settle(settle_ms)
                        active_route = window._workspace.current_workspace_key()
                        if active_route != route:
                            raise RuntimeError(
                                f"Route {route!r} did not activate; current={active_route!r}"
                            )
                        _stabilize_window_geometry(
                            window,
                            width=width,
                            height=height,
                            settle_ms=settle_ms,
                        )
                        filename = f"{locale}__{route}.png"
                        target = capture_dir / filename
                        _capture_window(window, target)
                        captures.append(
                            {
                                "locale": locale,
                                "route": route,
                                "file": str(target.relative_to(session_dir)),
                                "captured_at": datetime.now(UTC).isoformat(),
                                "width": window.width(),
                                "height": window.height(),
                            }
                        )
            finally:
                _shutdown_window(app, window)
    except Exception as exc:
        failures = manifest["failures"]
        assert isinstance(failures, list)
        failures.append(
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "captured_at": datetime.now(UTC).isoformat(),
            }
        )
        _write_bundle(session_dir, manifest)
        raise
    finally:
        os.chdir(previous_cwd)

    return _write_bundle(session_dir, manifest)


def _slug(value: str) -> str:
    normalized = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in value.strip()
    ).strip("-")
    return normalized[:60] or "window"


def _visible_top_level_widgets(
    app: SafeApplication,
    window: MainWindow,
) -> tuple[QWidget, ...]:
    visible = [widget for widget in app.topLevelWidgets() if widget.isVisible()]
    return tuple(
        sorted(
            visible,
            key=lambda widget: (
                0 if widget is window else 1,
                type(widget).__name__,
                widget.objectName(),
                widget.windowTitle(),
            ),
        )
    )


class _InteractiveCaptureSession:
    def __init__(
        self,
        *,
        app: SafeApplication,
        window: MainWindow,
        localization: LocalizationManager,
        session_dir: Path,
        manifest: dict[str, object],
        capture_hotkey: str,
        exit_after_captures: int,
    ) -> None:
        self._app = app
        self._window = window
        self._localization = localization
        self._session_dir = session_dir
        self._manifest = manifest
        self._capture_index = 0
        self._exit_after_captures = max(0, exit_after_captures)
        sequence = QKeySequence(capture_hotkey)
        if sequence.isEmpty():
            raise ValueError(f"Invalid capture hotkey: {capture_hotkey!r}")
        self._shortcut = QShortcut(sequence, window)
        self._shortcut.setContext(Qt.ApplicationShortcut)
        self._shortcut.activated.connect(self.capture)

    @property
    def capture_count(self) -> int:
        return self._capture_index

    def capture(self) -> None:
        try:
            _settle(0)
            self._capture_index += 1
            record = self._capture_state(self._capture_index)
            captures = self._manifest["captures"]
            assert isinstance(captures, list)
            captures.append(record)
            bundle = _write_bundle(self._session_dir, self._manifest)
            print(
                "Visual capture "
                f"#{self._capture_index}: {record['locale']} / {record['route']} -> {bundle}",
                flush=True,
            )
            if (
                self._exit_after_captures
                and self._capture_index >= self._exit_after_captures
            ):
                QTimer.singleShot(0, self._app.quit)
        except Exception as exc:
            failures = self._manifest["failures"]
            assert isinstance(failures, list)
            failures.append(
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "captured_at": datetime.now(UTC).isoformat(),
                    "capture_index": self._capture_index,
                }
            )
            _write_bundle(self._session_dir, self._manifest)
            print(f"Visual capture failed: {exc}", file=sys.stderr, flush=True)

    def _capture_state(self, capture_index: int) -> dict[str, object]:
        capture_dir = self._session_dir / "interactive" / f"{capture_index:04d}"
        capture_dir.mkdir(parents=True, exist_ok=False)
        windows: list[dict[str, object]] = []
        for window_index, widget in enumerate(
            _visible_top_level_widgets(self._app, self._window)
        ):
            label = _slug(widget.objectName() or widget.windowTitle() or type(widget).__name__)
            target = capture_dir / f"{window_index:02d}__{label}.png"
            metadata = _capture_widget(widget, target)
            metadata["file"] = str(target.relative_to(self._session_dir))
            windows.append(metadata)

        state_path = capture_dir / "state.json"
        record: dict[str, object] = {
            "index": capture_index,
            "captured_at": datetime.now(UTC).isoformat(),
            "locale": self._localization.locale,
            "route": self._window._workspace.current_workspace_key(),
            "width": self._window.width(),
            "height": self._window.height(),
            "ui_scale": self._app.property("ptl_ui_scale"),
            "density": self._app.property("ptl_ui_density"),
            "theme": getattr(self._window, "_current_theme", ""),
            "accent": getattr(self._window, "_current_accent", ""),
            "windows": windows,
            "state_file": str(state_path.relative_to(self._session_dir)),
        }
        state_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return record


def run_interactive_visual_audit(
    *,
    output_root: Path,
    initial_locale: str,
    width: int,
    height: int,
    scale: str,
    theme: str,
    accent: str,
    settle_ms: int,
    capture_hotkey: str,
    capture_on_start: bool,
    exit_after_captures: int,
) -> tuple[Path, bool]:
    commit = _git("rev-parse", "HEAD")
    branch = _git("branch", "--show-current")
    status = _git("status", "--porcelain")
    routes = tuple(NAVIGATION_KEYS)
    session_dir = _session_directory(output_root, commit, "interactive")
    manifest = _new_manifest(
        mode="interactive",
        commit=commit,
        branch=branch,
        dirty=status not in {"", "unknown"},
        routes=routes,
        locales=(initial_locale,),
        width=width,
        height=height,
        scale=scale,
        theme=theme,
        accent=accent,
        settle_ms=settle_ms,
    )
    manifest["capture_hotkey"] = capture_hotkey

    previous_cwd = Path.cwd()
    app: SafeApplication | None = None
    window: MainWindow | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="ptl-visual-audit-") as workspace:
            os.chdir(workspace)
            try:
                app, window, localization = _build_window(
                    scale=scale,
                    theme=theme,
                    accent=accent,
                    initial_locale=initial_locale,
                )
                manifest["available_locales"] = list(localization.available_locales())
                if width > 0 and height > 0:
                    window.resize(width, height)
                    window.show()
                else:
                    window.showMaximized()
                _settle(settle_ms)

                session = _InteractiveCaptureSession(
                    app=app,
                    window=window,
                    localization=localization,
                    session_dir=session_dir,
                    manifest=manifest,
                    capture_hotkey=capture_hotkey,
                    exit_after_captures=exit_after_captures,
                )
                print(
                    f"Interactive visual audit: press {capture_hotkey} to capture current state.",
                    flush=True,
                )
                print(
                    "Arrange routes, locale, window size and docks freely; close the window to finish.",
                    flush=True,
                )
                if capture_on_start:
                    QTimer.singleShot(0, session.capture)
                app.exec()
            finally:
                _shutdown_window(app, window)
    except Exception as exc:
        failures = manifest["failures"]
        assert isinstance(failures, list)
        failures.append(
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "captured_at": datetime.now(UTC).isoformat(),
            }
        )
        _write_bundle(session_dir, manifest)
        raise
    finally:
        os.chdir(previous_cwd)

    bundle = _write_bundle(session_dir, manifest)
    failures = manifest["failures"]
    return bundle, bool(failures)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture Persona Training Lab workspaces through Qt.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--locale", action="append", dest="locales")
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_WIDTH,
        help="Optional fixed window width; omit with --height to use maximized mode.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_HEIGHT,
        help="Optional fixed window height; omit with --width to use maximized mode.",
    )
    parser.add_argument("--scale", default=DEFAULT_SCALE)
    parser.add_argument("--theme", default=DEFAULT_THEME)
    parser.add_argument("--accent", default=DEFAULT_ACCENT)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Open a manual audit session and capture the current Qt state by hotkey.",
    )
    parser.add_argument(
        "--capture-hotkey",
        default=DEFAULT_CAPTURE_HOTKEY,
        help=f"Interactive capture hotkey (default: {DEFAULT_CAPTURE_HOTKEY}).",
    )
    parser.add_argument(
        "--capture-on-start",
        action="store_true",
        help="Take one interactive capture immediately after the window is shown.",
    )
    parser.add_argument(
        "--exit-after-captures",
        type=int,
        default=0,
        help="Exit interactive mode after N captures; zero keeps it open.",
    )
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    locales = args.locales or ["ru-RU", "en-US"]
    width = max(960, args.width) if args.width > 0 else 0
    height = max(620, args.height) if args.height > 0 else 0
    if bool(width) != bool(height):
        parser.error("--width and --height must be supplied together")
    started = time.monotonic()
    try:
        if args.interactive:
            bundle, failed = run_interactive_visual_audit(
                output_root=args.output,
                initial_locale=locales[0],
                width=width,
                height=height,
                scale=str(args.scale),
                theme=str(args.theme),
                accent=str(args.accent),
                settle_ms=max(0, args.settle_ms),
                capture_hotkey=str(args.capture_hotkey),
                capture_on_start=bool(args.capture_on_start),
                exit_after_captures=max(0, args.exit_after_captures),
            )
        else:
            bundle = run_visual_audit(
                output_root=args.output,
                locales=locales,
                width=width,
                height=height,
                scale=str(args.scale),
                theme=str(args.theme),
                accent=str(args.accent),
                settle_ms=max(0, args.settle_ms),
            )
            failed = False
    except Exception as exc:
        print(f"Visual audit failed: {exc}", file=sys.stderr)
        return 1
    print(f"Visual audit bundle: {bundle}")
    print(f"Completed in {time.monotonic() - started:.2f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

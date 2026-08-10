from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "release-audit"
QUICK_TESTS = (
    "tests/test_window_state_store.py",
    "tests/test_i18n_catalogs.py",
    "tests/test_i18n_catalog_fragments.py",
    "tests/test_i18n_audit.py",
    "tests/test_sidebar_i18n.py",
    "tests/test_operations_center_i18n.py",
    "tests/test_dashboard_viewmodel.py",
    "tests/test_dashboard_i18n.py",
    "tests/test_profiles_connector.py",
    "tests/test_profiles_i18n.py",
    "tests/test_profile_creation_validation.py",
    "tests/test_profiles_write_path.py",
    "tests/test_datasets_connector.py",
    "tests/test_datasets_i18n.py",
    "tests/test_dataset_import_validation.py",
    "tests/test_training_connector.py",
    "tests/test_training_i18n.py",
    "tests/test_training_semantic_contracts.py",
    "tests/test_training_run_creation.py",
    "tests/test_training_runner.py",
    "tests/test_local_model_probe.py",
    "tests/test_model_versions_connector.py",
    "tests/test_model_version_statuses.py",
    "tests/test_snapshots_i18n.py",
    "tests/test_style_i18n.py",
    "tests/test_docs_service.py",
    "tests/test_docs_i18n.py",
    "tests/test_personality_battery_loader.py",
    "tests/test_experiments_connector.py",
    "tests/test_experiments_i18n.py",
    "tests/test_experiments_selected_model.py",
    "tests/test_portrait_semantic_contracts.py",
    "tests/test_key_binding_manager.py",
    "tests/test_key_binding_draft_session.py",
    "tests/test_key_bindings_direct_capture.py",
    "tests/test_key_bindings_screen_registration.py",
    "tests/test_agents_key_bindings.py",
    "tests/test_keybindings_i18n.py",
    "tests/test_agents_i18n.py",
    "tests/test_tests_connector.py",
    "tests/test_analysis_connector.py",
    "tests/test_lineage_workflow_context.py",
    "tests/test_evaluation_i18n.py",
    "tests/test_lineage_projection_service.py",
    "tests/test_lineage_atomic_snapshot.py",
    "tests/test_agents_atomic_lineage.py",
    "tests/test_agents_lineage_state.py",
    "tests/test_lineage_state_schema6_i18n.py",
    "tests/test_agents_lineage_layout_undo_chain.py",
    "tests/test_lineage_refresh_schedule.py",
    "tests/test_lineage_refresh_coordinator.py",
    "tests/test_lineage_projection_loader.py",
    "tests/test_agents_background_projection.py",
    "tests/test_agents_content_repaint.py",
    "tests/test_background_close_guard.py",
    "tests/test_lineage_projection_link_reconciliation.py",
    "tests/test_lineage_runtime_policy.py",
    "tests/test_lineage_runtime_safety.py",
    "tests/test_lineage_projection_runtime_components.py",
    "tests/test_lineage_projection_update_planner.py",
    "tests/test_agents_final_screen_route.py",
    "tests/test_history_shortcut_routing.py",
    "tests/test_agents_editable_key_binding_routing.py",
    "tests/test_agents_history_key_layouts.py",
    "tests/test_history_gesture_core.py",
    "tests/test_history_key_resolver.py",
    "tests/test_history_repeat_timers.py",
    "tests/test_agents_history_repeat_adapter.py",
    "tests/test_history_modifier_poller.py",
    "tests/test_agents_history_modifier_poller_adapter.py",
    "tests/test_history_modifier_snapshot.py",
    "tests/test_agents_history_modifier_snapshot_adapter.py",
    "tests/test_history_event_orchestrator.py",
    "tests/test_agents_history_event_adapter.py",
    "tests/test_lineage_context_navigation.py",
    "tests/test_agents_scroll_compensation.py",
    "tests/test_agents_context_adapter.py",
    "tests/test_lineage_atomic_state_store.py",
    "tests/test_branch_deletion_controller.py",
    "tests/test_branch_deletion_finalization_contract.py",
    "tests/test_agents_branch_deletion_adapter.py",
    "tests/test_sidebar_compact_shortcuts_and_canvas_scroll.py",
    "tests/test_navigation_shortcuts_and_zoom.py",
    "tests/test_workspace_leave_guard.py",
    "tests/test_runtime_operation_coordinator.py",
    "tests/test_atomic_runtime_operation_coordinator.py",
    "tests/test_runtime_destructive_lineage.py",
    "tests/test_application_error_reporter.py",
    "tests/test_qt_message_boundary.py",
)


@dataclass(frozen=True, slots=True)
class GateStep:
    name: str
    command: tuple[str, ...]
    blocking: bool = True


@dataclass(frozen=True, slots=True)
class StepResult:
    name: str
    command: tuple[str, ...]
    blocking: bool
    return_code: int
    duration_seconds: float
    log_path: str

    @property
    def passed(self) -> bool:
        return self.return_code == 0


class ReleaseGate:
    def __init__(
        self,
        *,
        output_root: Path,
        seed: int,
        runs: int,
        quick: bool,
        strict_mypy: bool,
        skip_mypy: bool,
        skip_build: bool,
    ) -> None:
        self._seed = seed
        self._runs = max(1, runs)
        self._quick = quick
        self._strict_mypy = strict_mypy
        self._skip_mypy = skip_mypy
        self._skip_build = skip_build
        self._metadata = self._collect_metadata()
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        commit = str(self._metadata.get("commit") or "unknown")[:12]
        self.output_dir = output_root / f"{stamp}-{commit}-seed-{seed}"
        self.output_dir.mkdir(parents=True, exist_ok=False)
        (self.output_dir / "metadata.json").write_text(
            json.dumps(self._metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def run(self) -> int:
        results: list[StepResult] = []
        print("Persona Training Lab release gate")
        print(f"Output: {self.output_dir}")
        print(f"Seed: {self._seed}")
        print(f"Test runs: {self._runs}")
        print()

        for step in self._setup_steps():
            result = self._run_step(step)
            results.append(result)
            if step.blocking and not result.passed:
                return self._finish(results)

        for run_index in range(1, self._runs + 1):
            step = self._pytest_step(run_index)
            result = self._run_step(step)
            results.append(result)
            if not result.passed:
                return self._finish(results)

        for step in self._final_steps():
            result = self._run_step(step)
            results.append(result)
            if step.blocking and not result.passed:
                return self._finish(results)

        return self._finish(results)

    def _setup_steps(self) -> tuple[GateStep, ...]:
        steps = [
            GateStep(
                "compileall",
                (
                    sys.executable,
                    "-m",
                    "compileall",
                    "-q",
                    "src",
                    "tests",
                    "tools",
                ),
            ),
            GateStep(
                "ruff",
                (
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "src",
                    "tests",
                    "tools",
                ),
            ),
        ]
        if not self._skip_mypy and not self._quick:
            steps.append(
                GateStep(
                    "mypy",
                    (sys.executable, "-m", "mypy", "src"),
                    blocking=self._strict_mypy,
                )
            )
        return tuple(steps)

    def _pytest_step(self, run_index: int) -> GateStep:
        command = [sys.executable, "-m", "pytest", "-q"]
        if self._quick:
            command.extend(QUICK_TESTS)
        return GateStep(
            f"pytest-run-{run_index:02d}",
            tuple(command),
        )

    def _final_steps(self) -> tuple[GateStep, ...]:
        steps = [
            GateStep(
                "i18n-audit",
                (
                    sys.executable,
                    "tools/i18n_audit.py",
                    "--json",
                ),
            ),
            GateStep(
                "codebase-stats",
                (
                    sys.executable,
                    "tools/codebase_stats.py",
                    "--json",
                ),
            ),
        ]
        if not self._skip_build and not self._quick:
            steps.append(GateStep("build", ("uv", "build")))
        return tuple(steps)

    def _run_step(self, step: GateStep) -> StepResult:
        log_path = self.output_dir / f"{step.name}.log"
        command_text = shlex.join(step.command)
        print(f"[{step.name}] {command_text}")
        started = time.monotonic()
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        env["PYTHONHASHSEED"] = str(self._seed)
        env["PTL_RELEASE_AUDIT"] = "1"
        env["PTL_RELEASE_AUDIT_DIR"] = str(self.output_dir)

        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"$ {command_text}\n\n")
            process = subprocess.Popen(
                step.command,
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert process.stdout is not None
            try:
                for line in process.stdout:
                    print(line, end="")
                    log.write(line)
            except KeyboardInterrupt:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise
            return_code = process.wait()

        duration = time.monotonic() - started
        status = "PASS" if return_code == 0 else (
            "WARN" if not step.blocking else "FAIL"
        )
        print(f"[{step.name}] {status} in {duration:.2f}s")
        print()
        return StepResult(
            name=step.name,
            command=step.command,
            blocking=step.blocking,
            return_code=return_code,
            duration_seconds=round(duration, 3),
            log_path=str(log_path.relative_to(self.output_dir)),
        )

    def _finish(self, results: Iterable[StepResult]) -> int:
        result_list = list(results)
        blocking_failures = [
            result
            for result in result_list
            if result.blocking and not result.passed
        ]
        warnings = [
            result
            for result in result_list
            if not result.blocking and not result.passed
        ]
        payload = {
            "passed": not blocking_failures,
            "seed": self._seed,
            "runs": self._runs,
            "quick": self._quick,
            "blocking_failures": [result.name for result in blocking_failures],
            "warnings": [result.name for result in warnings],
            "results": [
                asdict(result) | {"passed": result.passed}
                for result in result_list
            ],
        }
        (self.output_dir / "summary.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self._write_markdown_summary(payload)

        if blocking_failures:
            print("RELEASE GATE: FAIL")
            print(
                "Blocking failures: "
                + ", ".join(payload["blocking_failures"])
            )
            print(f"Logs: {self.output_dir}")
            return 1
        if warnings:
            print("RELEASE GATE: PASS WITH WARNINGS")
            print("Warnings: " + ", ".join(payload["warnings"]))
        else:
            print("RELEASE GATE: PASS")
        print(f"Report: {self.output_dir / 'summary.md'}")
        return 0

    def _write_markdown_summary(self, payload: dict[str, object]) -> None:
        lines = [
            "# Persona Training Lab release audit",
            "",
            f"- Result: **{'PASS' if payload['passed'] else 'FAIL'}**",
            f"- Commit: `{self._metadata.get('commit', 'unknown')}`",
            f"- Branch: `{self._metadata.get('branch', 'unknown')}`",
            f"- Seed: `{self._seed}`",
            f"- Test runs: `{self._runs}`",
            f"- Dirty worktree: `{self._metadata.get('dirty', False)}`",
            "",
            "| Step | Blocking | Result | Seconds | Log |",
            "|---|---:|---:|---:|---|",
        ]
        for result in payload["results"]:  # type: ignore[index]
            lines.append(
                "| {name} | {blocking} | {status} | {duration:.3f} | `{log}` |".format(
                    name=result["name"],
                    blocking="yes" if result["blocking"] else "no",
                    status="PASS" if result["passed"] else "FAIL",
                    duration=float(result["duration_seconds"]),
                    log=result["log_path"],
                )
            )
        warnings = payload["warnings"]
        if warnings:
            lines.extend(("", "## Informational failures", ""))
            lines.extend(
                f"- `{name}`" for name in warnings  # type: ignore[arg-type]
            )
        lines.append("")
        (self.output_dir / "summary.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

    def _collect_metadata(self) -> dict[str, object]:
        status = _git("status", "--porcelain")
        return {
            "created_at": datetime.now(UTC).isoformat(),
            "commit": _git("rev-parse", "HEAD") or "unknown",
            "branch": _git("branch", "--show-current") or "detached",
            "dirty": bool(status.strip()),
            "dirty_paths": status.splitlines(),
            "python": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "seed": self._seed,
            "runs": self._runs,
            "quick": self._quick,
        }


def _git(*args: str) -> str:
    try:
        completed = subprocess.run(
            ("git", *args),
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a reproducible Persona Training Lab release audit.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Root directory for isolated audit reports.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed recorded in the report and passed to child processes.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of complete pytest runs.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run the release-shell subset and skip mypy/build.",
    )
    parser.add_argument("--strict-mypy", action="store_true")
    parser.add_argument("--skip-mypy", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    seed = args.seed if args.seed is not None else secrets.randbits(32)
    gate = ReleaseGate(
        output_root=args.output.resolve(),
        seed=seed,
        runs=args.runs,
        quick=args.quick,
        strict_mypy=args.strict_mypy,
        skip_mypy=args.skip_mypy,
        skip_build=args.skip_build,
    )
    try:
        return gate.run()
    except KeyboardInterrupt:
        print("\nRelease audit interrupted. Partial logs were preserved.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

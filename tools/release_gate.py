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
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "release-audit"
QUICK_TEST_MANIFEST = ROOT / "tools" / "release_quick_tests.txt"


class StepResultPayload(TypedDict):
    name: str
    command: tuple[str, ...]
    blocking: bool
    return_code: int
    duration_seconds: float
    log_path: str
    passed: bool


class AuditSummary(TypedDict):
    passed: bool
    seed: int
    runs: int
    quick: bool
    blocking_failures: list[str]
    warnings: list[str]
    results: list[StepResultPayload]


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

    def to_payload(self) -> StepResultPayload:
        return {
            "name": self.name,
            "command": self.command,
            "blocking": self.blocking,
            "return_code": self.return_code,
            "duration_seconds": self.duration_seconds,
            "log_path": self.log_path,
            "passed": self.passed,
        }


def load_quick_test_manifest(
    path: Path = QUICK_TEST_MANIFEST,
) -> tuple[str, ...]:
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RuntimeError(
            f"Quick test manifest is unavailable: {path}"
        ) from error

    tests = tuple(
        line
        for raw_line in raw_lines
        if (line := raw_line.strip()) and not line.startswith("#")
    )
    if not tests:
        raise RuntimeError(f"Quick test manifest is empty: {path}")

    duplicates = sorted(
        test for test in set(tests) if tests.count(test) > 1
    )
    if duplicates:
        raise RuntimeError(
            "Quick test manifest contains duplicate paths: "
            + ", ".join(duplicates)
        )

    missing = [test for test in tests if not (ROOT / test).is_file()]
    if missing:
        raise RuntimeError(
            "Quick test manifest references missing files: "
            + ", ".join(missing)
        )
    return tests


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
        self._quick_tests = load_quick_test_manifest()
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
        print(
            "Quick test manifest: "
            f"{QUICK_TEST_MANIFEST.relative_to(ROOT)} "
            f"({len(self._quick_tests)} tests)"
        )
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
            command.extend(self._quick_tests)
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
            stdout = process.stdout
            if stdout is None:
                process.kill()
                process.wait()
                raise RuntimeError(
                    f"Failed to capture output for gate step: {step.name}"
                )
            try:
                for line in stdout:
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
        payload: AuditSummary = {
            "passed": not blocking_failures,
            "seed": self._seed,
            "runs": self._runs,
            "quick": self._quick,
            "blocking_failures": [
                result.name for result in blocking_failures
            ],
            "warnings": [result.name for result in warnings],
            "results": [result.to_payload() for result in result_list],
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

    def _write_markdown_summary(self, payload: AuditSummary) -> None:
        lines = [
            "# Persona Training Lab release audit",
            "",
            f"- Result: **{'PASS' if payload['passed'] else 'FAIL'}**",
            f"- Commit: `{self._metadata.get('commit', 'unknown')}`",
            f"- Branch: `{self._metadata.get('branch', 'unknown')}`",
            f"- Seed: `{self._seed}`",
            f"- Test runs: `{self._runs}`",
            f"- Dirty worktree: `{self._metadata.get('dirty', False)}`",
            f"- Quick tests: `{len(self._quick_tests)}`",
            "",
            "| Step | Blocking | Result | Seconds | Log |",
            "|---|---:|---:|---:|---|",
        ]
        for result in payload["results"]:
            lines.append(
                "| {name} | {blocking} | {status} | {duration:.3f} | `{log}` |".format(
                    name=result["name"],
                    blocking="yes" if result["blocking"] else "no",
                    status="PASS" if result["passed"] else "FAIL",
                    duration=result["duration_seconds"],
                    log=result["log_path"],
                )
            )
        if payload["warnings"]:
            lines.extend(("", "## Informational failures", ""))
            lines.extend(f"- `{name}`" for name in payload["warnings"])
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
            "quick_test_manifest": str(QUICK_TEST_MANIFEST.relative_to(ROOT)),
            "quick_test_count": len(self._quick_tests),
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
        help="Run the curated quick manifest and skip mypy/build.",
    )
    parser.add_argument("--strict-mypy", action="store_true")
    parser.add_argument("--skip-mypy", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    seed = args.seed if args.seed is not None else secrets.randbits(32)
    try:
        gate = ReleaseGate(
            output_root=args.output.resolve(),
            seed=seed,
            runs=args.runs,
            quick=args.quick,
            strict_mypy=args.strict_mypy,
            skip_mypy=args.skip_mypy,
            skip_build=args.skip_build,
        )
        return gate.run()
    except RuntimeError as error:
        print(f"Release audit configuration error: {error}")
        return 2
    except KeyboardInterrupt:
        print("\nRelease audit interrupted. Partial logs were preserved.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

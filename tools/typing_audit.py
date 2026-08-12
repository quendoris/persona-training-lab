from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
CONFIG_PATHS = (
    ROOT / "pyproject.toml",
    ROOT / "mypy.ini",
    ROOT / ".mypy.ini",
    ROOT / "setup.cfg",
    ROOT / "tox.ini",
)

_SOURCE_MARKERS = (
    (
        "type_ignore",
        re.compile(r"#\s*type:\s*ignore(?:\s*\[[^\]]*\])?"),
    ),
    (
        "mypy_ignore_errors",
        re.compile(r"#\s*mypy:\s*ignore-errors\b", re.IGNORECASE),
    ),
    (
        "mypy_disable_error_code",
        re.compile(
            r"#\s*mypy:\s*disable[-_]error[-_]code\b",
            re.IGNORECASE,
        ),
    ),
)

_CONFIG_MARKERS = (
    (
        "mypy_ignore_errors_config",
        re.compile(r"^\s*ignore_errors\s*=\s*true\s*(?:#.*)?$", re.IGNORECASE),
    ),
    (
        "mypy_disable_error_code_config",
        re.compile(r"^\s*disable_error_code\s*=", re.IGNORECASE),
    ),
)


@dataclass(frozen=True, slots=True)
class TypingSuppressionFinding:
    path: str
    line: int
    kind: str
    text: str


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _scan_file(
    path: Path,
    *,
    root: Path,
    markers: tuple[tuple[str, re.Pattern[str]], ...],
) -> list[TypingSuppressionFinding]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RuntimeError(f"Typing audit cannot read: {path}") from error

    findings: list[TypingSuppressionFinding] = []
    for line_number, line in enumerate(lines, start=1):
        for kind, pattern in markers:
            if pattern.search(line) is None:
                continue
            findings.append(
                TypingSuppressionFinding(
                    path=_relative(path, root),
                    line=line_number,
                    kind=kind,
                    text=line.strip(),
                )
            )
            break
    return findings


def scan_typing_suppressions(
    *,
    root: Path = ROOT,
    source_root: Path | None = None,
    config_paths: tuple[Path, ...] | None = None,
) -> tuple[TypingSuppressionFinding, ...]:
    source = source_root or root / "src"
    configs = config_paths or (
        root / "pyproject.toml",
        root / "mypy.ini",
        root / ".mypy.ini",
        root / "setup.cfg",
        root / "tox.ini",
    )

    findings: list[TypingSuppressionFinding] = []
    if source.is_dir():
        for path in sorted(source.rglob("*.py")):
            findings.extend(
                _scan_file(
                    path,
                    root=root,
                    markers=_SOURCE_MARKERS,
                )
            )

    for path in configs:
        if not path.is_file():
            continue
        findings.extend(
            _scan_file(
                path,
                root=root,
                markers=_CONFIG_MARKERS,
            )
        )

    return tuple(
        sorted(
            findings,
            key=lambda item: (item.path, item.line, item.kind),
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when production typing suppressions can hide mypy errors."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable audit payload.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        findings = scan_typing_suppressions()
    except RuntimeError as error:
        print(str(error))
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "passed": not findings,
                    "finding_count": len(findings),
                    "findings": [asdict(item) for item in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif findings:
        for finding in findings:
            print(
                f"{finding.path}:{finding.line}: "
                f"{finding.kind}: {finding.text}"
            )
    else:
        print("Typing suppression audit passed: no suppressions found.")

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

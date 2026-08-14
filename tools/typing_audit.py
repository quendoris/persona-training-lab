from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from io import StringIO
import json
from pathlib import Path
import re
from tokenize import COMMENT, TokenError, generate_tokens


ROOT = Path(__file__).resolve().parents[1]
CODE_ROOTS = (
    ROOT / "src",
    ROOT / "tests",
    ROOT / "tools",
)
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

_CODED_TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore\s*\[[^\]]+\]")


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


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"Typing audit cannot read: {path}") from error


def _scan_python_file(
    path: Path,
    *,
    root: Path,
) -> list[TypingSuppressionFinding]:
    text = _read_text(path)
    findings: list[TypingSuppressionFinding] = []
    try:
        tokens = generate_tokens(StringIO(text).readline)
        for token in tokens:
            if token.type != COMMENT:
                continue
            for kind, pattern in _SOURCE_MARKERS:
                if pattern.search(token.string) is None:
                    continue
                findings.append(
                    TypingSuppressionFinding(
                        path=_relative(path, root),
                        line=token.start[0],
                        kind=kind,
                        text=token.string.strip(),
                    )
                )
                break
    except (IndentationError, TokenError) as error:
        raise RuntimeError(f"Typing audit cannot tokenize: {path}") from error
    return findings


def _scan_config_file(
    path: Path,
    *,
    root: Path,
) -> list[TypingSuppressionFinding]:
    lines = _read_text(path).splitlines()
    findings: list[TypingSuppressionFinding] = []
    for line_number, line in enumerate(lines, start=1):
        for kind, pattern in _CONFIG_MARKERS:
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
    code_roots: tuple[Path, ...] | None = None,
    config_paths: tuple[Path, ...] | None = None,
) -> tuple[TypingSuppressionFinding, ...]:
    roots = (
        code_roots
        if code_roots is not None
        else (root / "src", root / "tests", root / "tools")
    )
    configs = (
        config_paths
        if config_paths is not None
        else (
            root / "pyproject.toml",
            root / "mypy.ini",
            root / ".mypy.ini",
            root / "setup.cfg",
            root / "tox.ini",
        )
    )

    findings: list[TypingSuppressionFinding] = []
    seen_paths: set[Path] = set()
    for code_root in roots:
        if not code_root.is_dir():
            continue
        for path in sorted(code_root.rglob("*.py")):
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            findings.extend(_scan_python_file(path, root=root))

    for path in configs:
        if not path.is_file():
            continue
        findings.extend(_scan_config_file(path, root=root))

    return tuple(
        sorted(
            findings,
            key=lambda item: (item.path, item.line, item.kind),
        )
    )


def _is_narrow_test_suppression(finding: TypingSuppressionFinding) -> bool:
    if not finding.path.startswith("tests/"):
        return False
    if finding.kind != "type_ignore":
        return False
    return _CODED_TYPE_IGNORE.search(finding.text) is not None


def classify_typing_suppressions(
    findings: tuple[TypingSuppressionFinding, ...],
) -> tuple[
    tuple[TypingSuppressionFinding, ...],
    tuple[TypingSuppressionFinding, ...],
]:
    blocking: list[TypingSuppressionFinding] = []
    informational: list[TypingSuppressionFinding] = []
    for finding in findings:
        if _is_narrow_test_suppression(finding):
            informational.append(finding)
        else:
            blocking.append(finding)
    return tuple(blocking), tuple(informational)


def _finding_payload(
    finding: TypingSuppressionFinding,
    *,
    blocking: bool,
) -> dict[str, object]:
    return {**asdict(finding), "blocking": blocking}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when typing suppressions can hide errors in production code, "
            "release tooling, or mypy config while inventorying narrow test seams."
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

    blocking, informational = classify_typing_suppressions(findings)
    blocking_ids = {id(finding) for finding in blocking}

    if args.json:
        print(
            json.dumps(
                {
                    "passed": not blocking,
                    "finding_count": len(findings),
                    "blocking_finding_count": len(blocking),
                    "informational_finding_count": len(informational),
                    "findings": [
                        _finding_payload(
                            item,
                            blocking=id(item) in blocking_ids,
                        )
                        for item in findings
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif findings:
        for finding in findings:
            severity = "BLOCK" if id(finding) in blocking_ids else "INFO"
            print(
                f"{severity} {finding.path}:{finding.line}: "
                f"{finding.kind}: {finding.text}"
            )
    else:
        print("Typing suppression audit passed: no suppressions found.")

    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())

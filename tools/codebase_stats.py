from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import tokenize
from typing import Iterable


TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".rst",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".ini",
    ".cfg",
    ".qss",
    ".css",
    ".svg",
    ".txt",
    ".sh",
}

IGNORED_TRACKED_FILES = {
    "uv.lock",
}


@dataclass(slots=True, frozen=True)
class FileStats:
    path: str
    category: str
    physical_lines: int
    nonblank_lines: int
    code_lines: int | None
    bytes_count: int


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _tracked_paths(root: Path) -> tuple[Path, ...]:
    raw = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    return tuple(
        root / item.decode("utf-8")
        for item in raw.split(b"\0")
        if item
    )


def _category(relative: str) -> str:
    suffix = Path(relative).suffix.casefold()
    if relative.startswith("src/") and suffix == ".py":
        return "Production Python"
    if relative.startswith("tests/") and suffix == ".py":
        return "Tests Python"
    if suffix == ".py":
        return "Tools Python"
    if relative.startswith("docs/") or suffix in {".md", ".rst"}:
        return "Documentation"
    if suffix in {".qss", ".css"}:
        return "Styles"
    if suffix == ".svg":
        return "SVG assets"
    if suffix in {".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"}:
        return "Configuration"
    if suffix in {".sh", ".txt"}:
        return "Other text"
    return "Other"


def _docstring_lines(source: str) -> set[int]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    result: set[int] = set()

    def collect(body: list[ast.stmt]) -> None:
        if not body:
            return
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            end = getattr(first, "end_lineno", first.lineno)
            result.update(range(first.lineno, end + 1))

    collect(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            collect(node.body)
    return result


def _python_code_lines(source: str) -> int:
    meaningful: set[int] = set()
    docstrings = _docstring_lines(source)
    ignored_types = {
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.NEWLINE,
        tokenize.NL,
        tokenize.COMMENT,
    }
    try:
        for token in tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__):
            if token.type in ignored_types:
                continue
            start, end = token.start[0], token.end[0]
            meaningful.update(
                line
                for line in range(start, end + 1)
                if line not in docstrings
            )
    except (IndentationError, tokenize.TokenError):
        return sum(1 for line in source.splitlines() if line.strip())
    return len(meaningful)


def _file_stats(root: Path, path: Path) -> FileStats | None:
    relative = path.relative_to(root).as_posix()
    if relative in IGNORED_TRACKED_FILES:
        return None
    if path.suffix.casefold() not in TEXT_SUFFIXES:
        return None
    try:
        raw = path.read_bytes()
        source = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    lines = source.splitlines()
    return FileStats(
        path=relative,
        category=_category(relative),
        physical_lines=len(lines),
        nonblank_lines=sum(1 for line in lines if line.strip()),
        code_lines=_python_code_lines(source) if path.suffix.casefold() == ".py" else None,
        bytes_count=len(raw),
    )


def _fmt(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _totals(files: Iterable[FileStats]) -> dict[str, int]:
    materialized = tuple(files)
    return {
        "files": len(materialized),
        "physical_lines": sum(item.physical_lines for item in materialized),
        "nonblank_lines": sum(item.nonblank_lines for item in materialized),
        "code_lines": sum(item.code_lines or 0 for item in materialized),
        "bytes": sum(item.bytes_count for item in materialized),
    }


def _print_table(stats: tuple[FileStats, ...], top: int) -> None:
    grouped: dict[str, list[FileStats]] = defaultdict(list)
    for item in stats:
        grouped[item.category].append(item)

    print("\nCodebase statistics")
    print("=" * 78)
    print(f"Branch : {_git('branch', '--show-current') or '(detached)'}")
    print(f"Commit : {_git('rev-parse', '--short', 'HEAD')}")
    print()
    print(
        f"{'Category':<22} {'Files':>7} {'Physical':>11} "
        f"{'Nonblank':>11} {'Python code':>12}"
    )
    print("-" * 78)
    for category in (
        "Production Python",
        "Tests Python",
        "Tools Python",
        "Documentation",
        "Styles",
        "SVG assets",
        "Configuration",
        "Other text",
        "Other",
    ):
        items = grouped.get(category, [])
        if not items:
            continue
        total = _totals(items)
        code = _fmt(total["code_lines"]) if any(item.code_lines is not None for item in items) else "—"
        print(
            f"{category:<22} {_fmt(total['files']):>7} "
            f"{_fmt(total['physical_lines']):>11} "
            f"{_fmt(total['nonblank_lines']):>11} {code:>12}"
        )

    overall = _totals(stats)
    python_items = tuple(item for item in stats if item.code_lines is not None)
    python_total = _totals(python_items)
    production = _totals(grouped.get("Production Python", []))
    tests = _totals(grouped.get("Tests Python", []))

    print("-" * 78)
    print(
        f"{'Tracked text total':<22} {_fmt(overall['files']):>7} "
        f"{_fmt(overall['physical_lines']):>11} "
        f"{_fmt(overall['nonblank_lines']):>11} {'—':>12}"
    )
    print(
        f"{'All Python':<22} {_fmt(python_total['files']):>7} "
        f"{_fmt(python_total['physical_lines']):>11} "
        f"{_fmt(python_total['nonblank_lines']):>11} "
        f"{_fmt(python_total['code_lines']):>12}"
    )

    ratio = tests["code_lines"] / production["code_lines"] if production["code_lines"] else 0.0
    print()
    print(f"Production Python code : {_fmt(production['code_lines'])} lines")
    print(f"Tests Python code      : {_fmt(tests['code_lines'])} lines")
    print(f"Test / production ratio: {ratio:.2f}")

    largest = sorted(stats, key=lambda item: item.physical_lines, reverse=True)[:top]
    if largest:
        print(f"\nLargest {len(largest)} tracked text files")
        print("-" * 78)
        for item in largest:
            print(f"{_fmt(item.physical_lines):>8}  {item.path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count tracked project lines without external dependencies.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--top", type=int, default=15, help="Show N largest files.")
    args = parser.parse_args()

    root = Path(_git("rev-parse", "--show-toplevel"))
    stats = tuple(
        item
        for path in _tracked_paths(root)
        if (item := _file_stats(root, path)) is not None
    )

    if args.json:
        payload = {
            "branch": _git("branch", "--show-current") or "(detached)",
            "commit": _git("rev-parse", "--short", "HEAD"),
            "totals": _totals(stats),
            "categories": {
                category: _totals(item for item in stats if item.category == category)
                for category in sorted({item.category for item in stats})
            },
            "files": [
                {
                    "path": item.path,
                    "category": item.category,
                    "physical_lines": item.physical_lines,
                    "nonblank_lines": item.nonblank_lines,
                    "code_lines": item.code_lines,
                    "bytes": item.bytes_count,
                }
                for item in stats
            ],
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    _print_table(stats, max(0, args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

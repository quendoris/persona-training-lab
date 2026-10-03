from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
import tomllib
from typing import TypedDict
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
_INLINE_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
_REFERENCE_TARGET_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(\S+)")
_FENCE_RE = re.compile(r"^\s*((?:\x60){3,}|~~~+)")


class LinkIssue(TypedDict):
    source: str
    target: str
    resolved: str


class DocsAuditPayload(TypedDict):
    passed: bool
    markdown_files: int
    internal_links_checked: int
    missing_link_targets: list[LinkIssue]
    runtime_topics: list[str]
    missing_runtime_topics: list[str]
    wheel_docs_force_include: str
    wheel_docs_force_include_ok: bool


def _git_tracked_paths(root: Path) -> tuple[Path, ...]:
    completed = subprocess.run(
        ("git", "ls-files", "-z"),
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("docs audit requires a Git worktree")
    raw = completed.stdout.decode("utf-8", errors="strict")
    return tuple(Path(item) for item in raw.split("\0") if item)


def _markdown_text_without_fences(text: str) -> str:
    kept: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        match = _FENCE_RE.match(line)
        if match:
            marker_char = match.group(1)[0]
            if fence is None:
                fence = marker_char
            elif fence == marker_char:
                fence = None
            continue
        if fence is None:
            kept.append(line)
    return "\n".join(kept)


def _link_targets(text: str) -> tuple[str, ...]:
    visible = _markdown_text_without_fences(text)
    targets = [match.group(1).strip() for match in _INLINE_LINK_RE.finditer(visible)]
    for line in visible.splitlines():
        match = _REFERENCE_TARGET_RE.match(line)
        if match:
            targets.append(match.group(1).strip())
    return tuple(targets)


def _normalize_local_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if not target:
        return None
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")].strip()
    elif any(char.isspace() for char in target):
        target = target.split(maxsplit=1)[0]

    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith("#"):
        return None

    path = unquote(parsed.path)
    if not path:
        return None
    return path


def _resolve_target(root: Path, source: Path, target: str) -> Path:
    candidate = (
        root / target.lstrip("/")
        if target.startswith("/")
        else source.parent / target
    )
    return candidate.resolve()


def _runtime_topic_paths(root: Path) -> tuple[str, ...]:
    service_path = root / "src/persona_training_lab/application/docs/service.py"
    tree = ast.parse(
        service_path.read_text(encoding="utf-8"),
        filename=str(service_path),
    )
    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "DOC_TOPICS"
            for target in node.targets
        ):
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "DOC_TOPICS"
        ):
            value = node.value
        if not isinstance(value, (ast.Tuple, ast.List)):
            continue

        paths: list[str] = []
        for item in value.elts:
            if (
                isinstance(item, ast.Call)
                and len(item.args) >= 2
                and isinstance(item.args[1], ast.Constant)
                and isinstance(item.args[1].value, str)
            ):
                paths.append(item.args[1].value)
        return tuple(paths)
    raise RuntimeError(
        "DOC_TOPICS could not be resolved from application/docs/service.py"
    )


def audit_docs(root: Path = ROOT) -> DocsAuditPayload:
    root = root.resolve()
    tracked = _git_tracked_paths(root)
    markdown_paths = tuple(
        path
        for path in tracked
        if path.suffix.lower() == ".md" and (root / path).is_file()
    )

    missing_links: list[LinkIssue] = []
    checked = 0
    for relative_source in markdown_paths:
        source = root / relative_source
        for raw_target in _link_targets(source.read_text(encoding="utf-8")):
            target = _normalize_local_target(raw_target)
            if target is None:
                continue
            checked += 1
            resolved = _resolve_target(root, source, target)
            try:
                resolved.relative_to(root)
            except ValueError:
                missing_links.append(
                    {
                        "source": relative_source.as_posix(),
                        "target": raw_target,
                        "resolved": str(resolved),
                    }
                )
                continue
            if not resolved.exists():
                missing_links.append(
                    {
                        "source": relative_source.as_posix(),
                        "target": raw_target,
                        "resolved": resolved.relative_to(root).as_posix(),
                    }
                )

    runtime_topics = list(_runtime_topic_paths(root))
    missing_runtime = [
        path for path in runtime_topics if not (root / path).is_file()
    ]

    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = (
        pyproject.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("force-include", {})
    )
    wheel_target = str(force_include.get("docs", ""))
    wheel_ok = wheel_target == "persona_training_lab/docs"

    passed = not missing_links and not missing_runtime and wheel_ok
    return {
        "passed": passed,
        "markdown_files": len(markdown_paths),
        "internal_links_checked": checked,
        "missing_link_targets": missing_links,
        "runtime_topics": runtime_topics,
        "missing_runtime_topics": missing_runtime,
        "wheel_docs_force_include": wheel_target,
        "wheel_docs_force_include_ok": wheel_ok,
    }


def _print_human(payload: DocsAuditPayload) -> None:
    print("Persona Training Lab documentation audit")
    print(f"Markdown files: {payload['markdown_files']}")
    print(f"Internal links checked: {payload['internal_links_checked']}")
    print(f"Runtime topics: {len(payload['runtime_topics'])}")
    print(
        "Wheel docs force-include: "
        + (
            "PASS"
            if payload["wheel_docs_force_include_ok"]
            else f"FAIL ({payload['wheel_docs_force_include'] or 'missing'})"
        )
    )
    if payload["missing_runtime_topics"]:
        print("Missing runtime topics:")
        for path in payload["missing_runtime_topics"]:
            print(f"  - {path}")
    if payload["missing_link_targets"]:
        print("Missing/internal-invalid link targets:")
        for issue in payload["missing_link_targets"]:
            print(
                f"  - {issue['source']}: {issue['target']} -> {issue['resolved']}"
            )
    print("DOCS AUDIT: " + ("PASS" if payload["passed"] else "FAIL"))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit PTL Markdown links and runtime documentation packaging.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        payload = audit_docs()
    except (OSError, RuntimeError, UnicodeError, ValueError) as error:
        if args.json:
            print(
                json.dumps(
                    {"passed": False, "error": str(error)},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"DOCS AUDIT: FAIL ({error})")
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_human(payload)
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

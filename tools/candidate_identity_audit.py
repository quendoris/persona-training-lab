from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def audit_candidate_identity(
    root: Path,
    expected_commit: str,
) -> dict[str, object]:
    root = root.resolve()
    expected = expected_commit.strip()

    head_result = _git(root, "rev-parse", "HEAD")
    status_result = _git(root, "status", "--porcelain")
    current = head_result.stdout.strip() if head_result.returncode == 0 else ""
    dirty_paths = (
        status_result.stdout.splitlines()
        if status_result.returncode == 0
        else []
    )

    passed = bool(
        expected
        and head_result.returncode == 0
        and status_result.returncode == 0
        and current == expected
        and not dirty_paths
    )
    return {
        "expected_commit": expected,
        "current_commit": current,
        "head_resolved": head_result.returncode == 0,
        "status_resolved": status_result.returncode == 0,
        "dirty": bool(dirty_paths),
        "dirty_paths": dirty_paths,
        "passed": passed,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a release candidate still matches its recorded clean "
            "Git commit."
        ),
    )
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = audit_candidate_identity(ROOT, args.expected_commit)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if payload["passed"] else "FAIL"
        current = payload["current_commit"] or "unresolved"
        print(
            "candidate identity: "
            f"{status} "
            f"(expected={payload['expected_commit']}, "
            f"current={current}, dirty={payload['dirty']})"
        )
        for path in payload["dirty_paths"]:
            print(f"  {path}")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

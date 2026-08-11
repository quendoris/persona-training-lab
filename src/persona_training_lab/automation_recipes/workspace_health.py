from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3


EXPECTED_DIRECTORIES = ("artifacts", "exports", "temp", "cache")


def _database_report(path: Path) -> dict[str, object]:
    report: dict[str, object] = {
        "path": str(path),
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else 0,
        "tables": [],
    }
    if not path.is_file():
        return report
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    finally:
        connection.close()
    report["tables"] = [str(row[0]) for row in rows]
    return report


def build_report(workspace: Path) -> dict[str, object]:
    root = workspace.expanduser().resolve()
    directories = {
        name: {
            "path": str(root / name),
            "exists": (root / name).is_dir(),
        }
        for name in EXPECTED_DIRECTORIES
    }
    return {
        "schema": "ptl:automation-output:workspace-health:v1",
        "status": "ok" if root.is_dir() else "workspace_missing",
        "generated_at": datetime.now(UTC).isoformat(),
        "workspace": str(root),
        "directories": directories,
        "database": _database_report(root / "app.db"),
    }


def main() -> int:
    workspace = Path(os.environ.get("PTL_WORKSPACE") or Path.cwd())
    report = build_report(workspace)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import ast
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN_HISTORY_MODULES = frozenset(
    {
        "history_key_state",
        "history_gesture_lifecycle",
    }
)


def _retired_history_imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.rsplit(".", 1)[-1] in _FORBIDDEN_HISTORY_MODULES:
                violations.append((node.lineno, module))
            continue

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.rsplit(".", 1)[-1] in _FORBIDDEN_HISTORY_MODULES:
                    violations.append((node.lineno, alias.name))

    return violations


def test_retired_history_state_modules_have_no_importers() -> None:
    violations: list[str] = []

    for root_name in ("src", "tests"):
        for path in sorted((_ROOT / root_name).rglob("*.py")):
            for line_number, module in _retired_history_imports(path):
                relative_path = path.relative_to(_ROOT)
                violations.append(f"{relative_path}:{line_number}: {module}")

    assert violations == [], (
        "Retired history state modules are still imported:\n"
        + "\n".join(violations)
    )

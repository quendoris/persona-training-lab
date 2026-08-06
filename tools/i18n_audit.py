from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from persona_training_lab.i18n.catalog import (
    CatalogSet,
    CatalogValidationError,
)


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "persona_training_lab"
CATALOGS = SRC / "i18n" / "catalogs"
_TRANSLATION_KEY_POSITIONS = {
    "text": 0,
    "_text": 0,
    "bind_text": 1,
    "bind_tooltip": 1,
    "bind_window_title": 1,
    "bind_placeholder": 1,
}
_TRANSLATION_FALLBACK_POSITIONS = {
    "_text": (1,),
}
_WIDGET_TEXT_CALLS = {
    "QAction": (0,),
    "QCheckBox": (0,),
    "QDockWidget": (0,),
    "QGroupBox": (0,),
    "QLabel": (0,),
    "QMenu": (0,),
    "QPushButton": (0,),
    "QRadioButton": (0,),
    "PanelCard": (0, 1),
    "make_muted_label": (0,),
    "make_status_label": (0,),
}
_WIDGET_TEXT_METHODS = {
    "addAction": (0,),
    "addItem": (0,),
    "setPlaceholderText": (0,),
    "setStatusTip": (0,),
    "setTabText": (1,),
    "setText": (0,),
    "setToolTip": (0,),
    "setWhatsThis": (0,),
    "setWindowTitle": (0,),
}


@dataclass(frozen=True, slots=True)
class LiteralFinding:
    path: str
    line: int
    call: str
    text: str


class SourceAudit(ast.NodeVisitor):
    def __init__(
        self,
        path: Path,
        *,
        known_keys: frozenset[str] = frozenset(),
    ) -> None:
        self._path = path
        self._known_keys = known_keys
        self.translation_keys: set[str] = set()
        self.literals: list[LiteralFinding] = []

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node.func)
        key_position = _TRANSLATION_KEY_POSITIONS.get(call_name)
        if key_position is not None:
            key = _constant_argument(
                node,
                key_position,
                keyword="key",
            )
            if key is not None:
                self.translation_keys.add(key)
        fallback_positions = _TRANSLATION_FALLBACK_POSITIONS.get(call_name)
        if fallback_positions is not None:
            self._collect_literals(
                node,
                f"{call_name} fallback",
                fallback_positions,
            )
        if call_name in _WIDGET_TEXT_CALLS:
            self._collect_literals(
                node,
                call_name,
                _WIDGET_TEXT_CALLS[call_name],
            )
        if call_name in _WIDGET_TEXT_METHODS:
            self._collect_literals(
                node,
                call_name,
                _WIDGET_TEXT_METHODS[call_name],
            )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        value = node.value
        if isinstance(value, str) and value in self._known_keys:
            self.translation_keys.add(value)

    def _collect_literals(
        self,
        node: ast.Call,
        call_name: str,
        positions: tuple[int, ...],
    ) -> None:
        for position in positions:
            text = _constant_string(node.args, position)
            if text is None or not _looks_user_visible(text):
                continue
            self.literals.append(
                LiteralFinding(
                    path=_display_path(self._path),
                    line=node.lineno,
                    call=call_name,
                    text=" ".join(text.split()),
                )
            )


def audit_sources(
    *,
    catalog_keys: set[str] | frozenset[str] = frozenset(),
) -> tuple[set[str], list[LiteralFinding]]:
    keys: set[str] = set()
    literals: list[LiteralFinding] = []
    known_keys = frozenset(catalog_keys)
    for path in sorted(SRC.rglob("*.py")):
        if "i18n/catalogs" in path.as_posix():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            raise CatalogValidationError(
                f"Cannot parse {path}: {error}"
            ) from error
        visitor = SourceAudit(path, known_keys=known_keys)
        visitor.visit(tree)
        keys.update(visitor.translation_keys)
        literals.extend(visitor.literals)
    return keys, literals


def run(*, strict_ui_literals: bool, as_json: bool) -> int:
    try:
        catalogs = CatalogSet.load(CATALOGS, base_locale="ru-RU")
        base_keys = set(catalogs.catalog(catalogs.base_locale).messages)
        referenced_keys, literals = audit_sources(catalog_keys=base_keys)
    except CatalogValidationError as error:
        if as_json:
            print(json.dumps({"passed": False, "error": str(error)}))
        else:
            print(f"i18n audit failed: {error}")
        return 1

    missing_references = sorted(referenced_keys - base_keys)
    orphaned_keys = sorted(base_keys - referenced_keys)
    passed = not missing_references and not (
        strict_ui_literals and literals
    )
    payload = {
        "passed": passed,
        "base_locale": catalogs.base_locale,
        "locales": list(catalogs.available_locales()),
        "catalog_keys": len(base_keys),
        "referenced_keys": len(referenced_keys),
        "missing_references": missing_references,
        "orphaned_keys": orphaned_keys,
        "ui_literal_count": len(literals),
        "ui_literals": [asdict(item) for item in literals],
        "strict_ui_literals": strict_ui_literals,
    }

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Persona Training Lab i18n audit")
        print(f"Locales: {', '.join(payload['locales'])}")
        print(f"Catalog keys: {payload['catalog_keys']}")
        print(f"Referenced keys: {payload['referenced_keys']}")
        print(f"Hard-coded UI literals: {payload['ui_literal_count']}")
        if missing_references:
            print("Missing translation keys:")
            for key in missing_references:
                print(f"  - {key}")
        if literals:
            print("Hard-coded UI inventory:")
            for finding in literals[:100]:
                print(
                    f"  - {finding.path}:{finding.line} "
                    f"[{finding.call}] {finding.text}"
                )
            if len(literals) > 100:
                print(f"  ... {len(literals) - 100} more")
        if orphaned_keys:
            print(
                "Catalog keys not referenced by Python yet: "
                + ", ".join(orphaned_keys)
            )
        print("I18N AUDIT: " + ("PASS" if passed else "FAIL"))
    return 0 if passed else 1


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _constant_argument(
    node: ast.Call,
    position: int,
    *,
    keyword: str,
) -> str | None:
    positional = _constant_string(node.args, position)
    if positional is not None:
        return positional
    for item in node.keywords:
        if item.arg != keyword:
            continue
        if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
            return item.value.value
    return None


def _constant_string(args: list[ast.expr], index: int) -> str | None:
    if index >= len(args):
        return None
    node = args[index]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _looks_user_visible(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped in {"—", "-", "…"}:
        return False
    if stripped.startswith(("http://", "https://", "#")):
        return False
    return any(character.isalpha() for character in stripped)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate complete PTL locale catalogs and UI text usage.",
    )
    parser.add_argument(
        "--strict-ui-literals",
        action="store_true",
        help="Fail when user-visible widget text remains hard-coded.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return run(
        strict_ui_literals=args.strict_ui_literals,
        as_json=args.json,
    )


if __name__ == "__main__":
    raise SystemExit(main())

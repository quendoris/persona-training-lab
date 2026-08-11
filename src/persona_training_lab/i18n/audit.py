from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from persona_training_lab.i18n.catalog import (
    CatalogSet,
    CatalogValidationError,
)


_TRANSLATION_KEY_POSITIONS = {
    "text": 0,
    "_text": 0,
    "bind_text": 1,
    "bind_title": 1,
    "bind_tooltip": 1,
    "bind_window_title": 1,
    "bind_placeholder": 1,
    "UserMessage": 0,
    "DatasetText": 0,
    "dataset_text": 0,
    "ProfileText": 0,
    "profile_text": 0,
    "TrainingText": 0,
    "training_text": 0,
    "EvaluationText": 0,
    "evaluation_text": 0,
    "DashboardText": 0,
    "dashboard_text": 0,
    "SnapshotText": 0,
    "snapshot_text": 0,
    "AutomationText": 0,
    "automation_text": 0,
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
    "setTitle": (0,),
    "setToolTip": (0,),
    "setWhatsThis": (0,),
    "setWindowTitle": (0,),
}
_STRUCTURED_TEXT_ARGUMENTS: dict[str, tuple[tuple[int, str], ...]] = {
    "AgentView": (
        (1, "title"),
        (2, "subtitle"),
        (3, "status"),
    ),
    "AgentRoleView": (
        (1, "title"),
        (2, "mission"),
        (3, "next_action"),
        (4, "status"),
    ),
    "VersionNodeView": (
        (2, "title"),
        (3, "subtitle"),
        (4, "status"),
    ),
    "ProjectedVersionNode": (
        (2, "title"),
        (3, "subtitle"),
        (4, "status"),
    ),
    "LineageVersionNode": (
        (2, "title"),
        (3, "subtitle"),
        (4, "status"),
    ),
    "AgentDetailView": (
        (0, "title"),
        (1, "body"),
        (2, "checks"),
        (3, "actions"),
    ),
}
_PAINTER_TEXT_CALLS = {"drawText", "drawStaticText"}
_USER_VISIBLE_KEYWORDS = {"legacy_message", "user_message"}
_DYNAMIC_PREFIX_NAMES = {"I18N_KEY_PREFIXES"}
_DYNAMIC_KEY_COLLECTION_SUFFIX = "_KEYS"


@dataclass(frozen=True, slots=True)
class LiteralFinding:
    path: str
    line: int
    call: str
    text: str


@dataclass(frozen=True, slots=True)
class AuditReport:
    passed: bool
    base_locale: str
    locales: tuple[str, ...]
    catalog_keys: int
    referenced_keys: int
    missing_references: tuple[str, ...]
    orphaned_keys: tuple[str, ...]
    ui_literals: tuple[LiteralFinding, ...]
    strict_ui_literals: bool

    @property
    def ui_literal_count(self) -> int:
        return len(self.ui_literals)

    def to_payload(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "base_locale": self.base_locale,
            "locales": list(self.locales),
            "catalog_keys": self.catalog_keys,
            "referenced_keys": self.referenced_keys,
            "missing_references": list(self.missing_references),
            "orphaned_keys": list(self.orphaned_keys),
            "ui_literal_count": self.ui_literal_count,
            "ui_literals": [asdict(item) for item in self.ui_literals],
            "strict_ui_literals": self.strict_ui_literals,
        }


class SourceAudit(ast.NodeVisitor):
    """Collect translation-key references and direct user-visible literals."""

    def __init__(
        self,
        path: Path,
        *,
        known_keys: frozenset[str] = frozenset(),
        display_root: Path | None = None,
    ) -> None:
        self._path = path
        self._known_keys = known_keys
        self._display_root = display_root
        self._is_ui_viewmodel = _is_ui_viewmodel_path(path)
        self.translation_keys: set[str] = set()
        self.translation_prefixes: set[str] = set()
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
        structured = _STRUCTURED_TEXT_ARGUMENTS.get(call_name)
        if structured is not None:
            self._collect_structured_literals(node, call_name, structured)
        if call_name in _PAINTER_TEXT_CALLS:
            self._collect_all_argument_literals(node, call_name)
        self._collect_keyword_literals(
            node,
            call_name,
            _USER_VISIBLE_KEYWORDS,
        )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        target_names = tuple(_target_name(target) for target in node.targets)
        if any(name in _DYNAMIC_PREFIX_NAMES for name in target_names):
            self.translation_prefixes.update(
                _constant_string_sequence(node.value)
            )
        if self._is_ui_viewmodel and any(
            name.endswith(_DYNAMIC_KEY_COLLECTION_SUFFIX)
            for name in target_names
            if name
        ):
            self.translation_keys.update(
                _dotted_string_values(node.value)
            )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is None:
            self.generic_visit(node)
            return
        target_name = _target_name(node.target)
        if target_name in _DYNAMIC_PREFIX_NAMES:
            self.translation_prefixes.update(
                _constant_string_sequence(node.value)
            )
        if (
            self._is_ui_viewmodel
            and target_name.endswith(_DYNAMIC_KEY_COLLECTION_SUFFIX)
        ):
            self.translation_keys.update(
                _dotted_string_values(node.value)
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
            self._append_literal(node, call_name, text)

    def _collect_structured_literals(
        self,
        node: ast.Call,
        call_name: str,
        arguments: tuple[tuple[int, str], ...],
    ) -> None:
        for position, keyword in arguments:
            value = _argument_expression(
                node,
                position,
                keyword=keyword,
            )
            if value is None:
                continue
            for text in _literal_strings(value):
                if not _looks_user_visible(text):
                    continue
                self._append_literal(
                    node,
                    f"{call_name} {keyword}",
                    text,
                )

    def _collect_all_argument_literals(
        self,
        node: ast.Call,
        call_name: str,
    ) -> None:
        for argument in node.args:
            for text in _literal_strings(argument):
                if not _looks_user_visible(text):
                    continue
                self._append_literal(node, call_name, text)

    def _collect_keyword_literals(
        self,
        node: ast.Call,
        call_name: str,
        keywords: set[str],
    ) -> None:
        for item in node.keywords:
            if item.arg not in keywords:
                continue
            if not isinstance(item.value, ast.Constant):
                continue
            text = item.value.value
            if not isinstance(text, str) or not _looks_user_visible(text):
                continue
            self._append_literal(
                node,
                f"{call_name} {item.arg}".strip(),
                text,
            )

    def _append_literal(
        self,
        node: ast.Call,
        call_name: str,
        text: str,
    ) -> None:
        self.literals.append(
            LiteralFinding(
                path=_display_path(self._path, self._display_root),
                line=node.lineno,
                call=call_name,
                text=" ".join(text.split()),
            )
        )


def audit_sources(
    source_root: Path,
    *,
    display_root: Path | None = None,
    catalog_keys: set[str] | frozenset[str] = frozenset(),
) -> tuple[set[str], list[LiteralFinding]]:
    keys: set[str] = set()
    literals: list[LiteralFinding] = []
    known_keys = frozenset(catalog_keys)

    for path in sorted(source_root.rglob("*.py")):
        try:
            tree = ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
            )
        except (OSError, SyntaxError) as error:
            raise CatalogValidationError(
                f"Cannot parse {path}: {error}"
            ) from error
        visitor = SourceAudit(
            path,
            known_keys=known_keys,
            display_root=display_root,
        )
        visitor.visit(tree)
        keys.update(visitor.translation_keys)
        for prefix in visitor.translation_prefixes:
            keys.update(
                key for key in known_keys if key.startswith(prefix)
            )
        literals.extend(visitor.literals)
    return keys, literals


def build_audit_report(
    *,
    catalog_directory: Path,
    source_root: Path,
    display_root: Path | None = None,
    base_locale: str = "ru-RU",
    strict_ui_literals: bool = False,
) -> AuditReport:
    catalogs = CatalogSet.load(
        catalog_directory,
        base_locale=base_locale,
    )
    base_keys = set(catalogs.catalog(catalogs.base_locale).messages)
    referenced_keys, literals = audit_sources(
        source_root,
        display_root=display_root,
        catalog_keys=base_keys,
    )
    missing_references = tuple(sorted(referenced_keys - base_keys))
    orphaned_keys = tuple(sorted(base_keys - referenced_keys))
    literal_tuple = tuple(literals)
    passed = not missing_references and not (
        strict_ui_literals and literal_tuple
    )
    return AuditReport(
        passed=passed,
        base_locale=catalogs.base_locale,
        locales=catalogs.available_locales(),
        catalog_keys=len(base_keys),
        referenced_keys=len(referenced_keys),
        missing_references=missing_references,
        orphaned_keys=orphaned_keys,
        ui_literals=literal_tuple,
        strict_ui_literals=strict_ui_literals,
    )


def render_text_report(report: AuditReport, *, literal_limit: int = 100) -> str:
    lines = [
        "Persona Training Lab i18n audit",
        f"Locales: {', '.join(report.locales)}",
        f"Catalog keys: {report.catalog_keys}",
        f"Referenced keys: {report.referenced_keys}",
        f"Hard-coded UI literals: {report.ui_literal_count}",
    ]
    if report.missing_references:
        lines.append("Missing translation keys:")
        lines.extend(f"  - {key}" for key in report.missing_references)
    if report.ui_literals:
        lines.append("Hard-coded UI inventory:")
        for finding in report.ui_literals[:literal_limit]:
            lines.append(
                f"  - {finding.path}:{finding.line} "
                f"[{finding.call}] {finding.text}"
            )
        hidden = report.ui_literal_count - literal_limit
        if hidden > 0:
            lines.append(f"  ... {hidden} more")
    if report.orphaned_keys:
        lines.append(
            "Catalog keys not referenced by Python yet: "
            + ", ".join(report.orphaned_keys)
        )
    lines.append("I18N AUDIT: " + ("PASS" if report.passed else "FAIL"))
    return "\n".join(lines)


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _target_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _constant_string_sequence(node: ast.expr) -> tuple[str, ...]:
    if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return ()
    values: list[str] = []
    for item in node.elts:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            values.append(item.value)
    return tuple(values)


def _dotted_string_values(node: ast.expr) -> tuple[str, ...]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,) if "." in node.value else ()
    if isinstance(node, ast.Dict):
        values: list[str] = []
        for value in node.values:
            values.extend(_dotted_string_values(value))
        return tuple(values)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = []
        for item in node.elts:
            values.extend(_dotted_string_values(item))
        return tuple(values)
    if isinstance(node, ast.IfExp):
        return _dotted_string_values(node.body) + _dotted_string_values(
            node.orelse
        )
    return ()


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


def _argument_expression(
    node: ast.Call,
    position: int,
    *,
    keyword: str,
) -> ast.expr | None:
    if position < len(node.args):
        return node.args[position]
    for item in node.keywords:
        if item.arg == keyword:
            return item.value
    return None


def _literal_strings(node: ast.expr) -> tuple[str, ...]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values: list[str] = []
        for item in node.elts:
            values.extend(_literal_strings(item))
        return tuple(values)
    return ()


def _constant_string(args: list[ast.expr], index: int) -> str | None:
    if index >= len(args):
        return None
    node = args[index]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_ui_viewmodel_path(path: Path) -> bool:
    parts = path.parts
    for index in range(len(parts) - 1):
        if parts[index] == "ui" and parts[index + 1] == "viewmodels":
            return True
    return False


def _display_path(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _looks_user_visible(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped in {"—", "-", "…"}:
        return False
    if stripped.startswith(("http://", "https://", "#")):
        return False
    return any(character.isalpha() for character in stripped)

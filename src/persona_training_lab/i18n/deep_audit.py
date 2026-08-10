from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from persona_training_lab.i18n.audit import AuditReport, LiteralFinding


_STRUCTURED_USER_TEXT: dict[str, tuple[tuple[int, str], ...]] = {
    "experiment_result": ((1, "message"),),
    "ExperimentRunResult": ((1, "message"),),
    "EvaluationMetric": ((0, "title"), (2, "note")),
    "EvaluationCase": ((0, "title"), (1, "note")),
    "_evaluation_metric": ((0, "title"), (2, "note")),
    "_evaluation_case": ((0, "title"), (1, "note_models")),
    "TrainingMetric": ((0, "title"), (2, "note")),
    "_training_metric": ((0, "title"), (2, "note")),
    "CheckpointView": ((0, "name"), (1, "note")),
    "_checkpoint_view": ((0, "name"), (1, "note")),
    "PersonalityVersionView": (
        (0, "title"),
        (1, "status"),
        (2, "note"),
    ),
    "_personality_version": (
        (0, "title"),
        (1, "status"),
        (2, "note"),
    ),
    "CompareMetric": ((0, "title"), (2, "note")),
    "_compare_metric": ((0, "title"), (2, "note")),
    "CompareSummary": (
        (0, "title"),
        (1, "subtitle"),
        (2, "profile_match"),
        (3, "stability"),
        (4, "contradiction"),
    ),
    "_compare_summary": (
        (0, "title"),
        (1, "subtitle"),
        (2, "profile_match"),
        (3, "stability"),
        (4, "contradiction"),
    ),
    "CompareSample": (
        (0, "title"),
        (1, "left_note"),
        (2, "right_note"),
    ),
    "_compare_sample": (
        (0, "title"),
        (1, "left_note"),
        (2, "right_note"),
    ),
    "TrainingConfigurationError": ((0, "message"),),
    "TrainingValidationError": ((0, "message"),),
}
_UI_VIEWMODEL_TEXT_ATTRIBUTES = frozenset(
    {
        "title",
        "subtitle",
        "status",
        "status_message",
        "selected_objects",
        "versions_status_message",
        "logs",
        "monitor_rows",
        "risk_title",
        "risk_body",
        "next_step",
        "local_model_status",
        "local_model_note",
        "local_inference_status",
        "progress_note",
        "setup_rows",
        "context_rows",
        "insights",
        "deltas",
    }
)
_PERSISTED_SEMANTIC_FIELDS = {
    "create_training_run": frozenset({"status"}),
    "start_full_finetune_run": frozenset({"status"}),
    "_set_terminal_error": frozenset({"status"}),
    "create_from_training_run": frozenset({"status", "quality_summary"}),
}
_USER_RESULT_FUNCTIONS = frozenset(
    {
        "approve_dataset",
        "compare_dataset_versions",
        "start_full_finetune_run",
    }
)
_OPAQUE_VALIDATED_CALLS = frozenset(
    {
        "ActionResult",
        "UserMessage",
        "DatasetText",
        "dataset_text",
        "TrainingText",
        "training_text",
        "EvaluationText",
        "evaluation_text",
    }
)


class DeepSurfaceAudit(ast.NodeVisitor):
    """Find source-language text hidden behind semantic/application surfaces.

    The ordinary source audit intentionally focuses on direct UI calls and
    explicitly modeled presentation DTOs. This second pass targets historical
    compatibility surfaces where text can still reach the UI without appearing
    in a QWidget call: application result objects, typed user-facing errors,
    legacy public fields on UI view models, and persisted semantic fields that
    must remain language-neutral.

    Semantic text constructors are opaque here because the ordinary audit
    validates their keys against complete catalogs. ``ActionResult`` is opaque
    because its application contract independently enforces lower-snake-case
    machine codes rather than human-readable messages.
    """

    def __init__(
        self,
        path: Path,
        *,
        display_root: Path | None = None,
    ) -> None:
        self._path = path
        self._display_root = display_root
        self._function_stack: list[str] = []
        self._class_stack: list[str] = []
        self._assignments: list[dict[str, tuple[str, ...]]] = []
        self._is_ui_viewmodel = _is_ui_viewmodel_path(path)
        self.literals: list[LiteralFinding] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_stack.append(node.name)
        self._assignments.append({})
        self.generic_visit(node)
        self._assignments.pop()
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_stack.append(node.name)
        self._assignments.append({})
        self.generic_visit(node)
        self._assignments.pop()
        self._function_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        fragments = _string_fragments(node.value)
        if self._assignments and fragments:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._assignments[-1][target.id] = fragments
        if self._is_ui_viewmodel:
            for target in node.targets:
                attribute = _self_attribute_name(target)
                if attribute in _UI_VIEWMODEL_TEXT_ATTRIBUTES:
                    self._append_fragments(
                        node,
                        f"self.{attribute}",
                        fragments,
                    )
                elif (
                    self._class_stack
                    and not self._function_stack
                    and isinstance(target, ast.Name)
                    and target.id in _UI_VIEWMODEL_TEXT_ATTRIBUTES
                ):
                    self._append_fragments(
                        node,
                        f"class.{target.id}",
                        fragments,
                    )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is None:
            self.generic_visit(node)
            return
        fragments = _string_fragments(node.value)
        if self._assignments and fragments and isinstance(node.target, ast.Name):
            self._assignments[-1][node.target.id] = fragments
        if self._is_ui_viewmodel:
            attribute = _self_attribute_name(node.target)
            if attribute in _UI_VIEWMODEL_TEXT_ATTRIBUTES:
                self._append_fragments(
                    node,
                    f"self.{attribute}",
                    fragments,
                )
            elif (
                self._class_stack
                and not self._function_stack
                and isinstance(node.target, ast.Name)
                and node.target.id in _UI_VIEWMODEL_TEXT_ATTRIBUTES
            ):
                self._append_fragments(
                    node,
                    f"class.{node.target.id}",
                    fragments,
                )
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        function_name = self._function_stack[-1] if self._function_stack else ""
        fields = _PERSISTED_SEMANTIC_FIELDS.get(function_name)
        if fields is not None:
            for key, value in zip(node.keys, node.values, strict=True):
                if (
                    not isinstance(key, ast.Constant)
                    or not isinstance(key.value, str)
                    or key.value not in fields
                ):
                    continue
                fragments = tuple(
                    fragment
                    for fragment in self._resolved_fragments(value)
                    if not _looks_machine_code(fragment)
                )
                self._append_fragments(
                    node,
                    f"{function_name} persisted {key.value}",
                    fragments,
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node.func)
        structured = _STRUCTURED_USER_TEXT.get(call_name)
        if structured is not None:
            for position, keyword in structured:
                expression = _argument_expression(
                    node,
                    position,
                    keyword=keyword,
                )
                if expression is None:
                    continue
                fragments = self._resolved_fragments(expression)
                self._append_fragments(
                    node,
                    f"{call_name} {keyword}",
                    fragments,
                )
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        function_name = self._function_stack[-1] if self._function_stack else ""
        if function_name in _USER_RESULT_FUNCTIONS and node.value is not None:
            fragments = self._resolved_fragments(node.value)
            self._append_fragments(
                node,
                f"{function_name} return",
                fragments,
            )
        self.generic_visit(node)

    def _resolved_fragments(self, expression: ast.expr) -> tuple[str, ...]:
        if isinstance(expression, ast.Name) and self._assignments:
            assigned = self._assignments[-1].get(expression.id)
            if assigned is not None:
                return assigned
        return _string_fragments(expression)

    def _append_fragments(
        self,
        node: ast.AST,
        call: str,
        fragments: tuple[str, ...],
    ) -> None:
        for fragment in fragments:
            if not _looks_user_visible(fragment):
                continue
            self.literals.append(
                LiteralFinding(
                    path=_display_path(self._path, self._display_root),
                    line=getattr(node, "lineno", 0),
                    call=call,
                    text=" ".join(fragment.split()),
                )
            )


def collect_deep_literals(
    source_root: Path,
    *,
    display_root: Path | None = None,
) -> tuple[LiteralFinding, ...]:
    findings: list[LiteralFinding] = []
    for path in sorted(source_root.rglob("*.py")):
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        visitor = DeepSurfaceAudit(path, display_root=display_root)
        visitor.visit(tree)
        findings.extend(visitor.literals)
    return tuple(findings)


def augment_report_with_deep_literals(
    report: AuditReport,
    *,
    source_root: Path,
    display_root: Path | None = None,
) -> AuditReport:
    combined = {
        (item.path, item.line, item.call, item.text): item
        for item in report.ui_literals
    }
    for item in collect_deep_literals(
        source_root,
        display_root=display_root,
    ):
        combined[(item.path, item.line, item.call, item.text)] = item
    literals = tuple(combined[key] for key in sorted(combined))
    passed = not report.missing_references and not (
        report.strict_ui_literals and literals
    )
    return replace(
        report,
        passed=passed,
        ui_literals=literals,
    )


def _is_ui_viewmodel_path(path: Path) -> bool:
    parts = path.parts
    for index in range(len(parts) - 1):
        if parts[index] == "ui" and parts[index + 1] == "viewmodels":
            return True
    return False


def _self_attribute_name(node: ast.expr) -> str:
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    ):
        return node.attr
    return ""


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


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


def _string_fragments(node: ast.expr) -> tuple[str, ...]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,)
    if isinstance(node, ast.JoinedStr):
        joined_fragments: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                joined_fragments.append(value.value)
        return tuple(joined_fragments)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        sequence_fragments: list[str] = []
        for item in node.elts:
            sequence_fragments.extend(_string_fragments(item))
        return tuple(sequence_fragments)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _string_fragments(node.left) + _string_fragments(node.right)
    if isinstance(node, ast.IfExp):
        return _string_fragments(node.body) + _string_fragments(node.orelse)
    if isinstance(node, ast.BoolOp):
        bool_fragments: list[str] = []
        for value in node.values:
            bool_fragments.extend(_string_fragments(value))
        return tuple(bool_fragments)
    if isinstance(node, ast.Call):
        if _call_name(node.func) in _OPAQUE_VALIDATED_CALLS:
            return ()
        call_fragments: list[str] = []
        for argument in node.args:
            call_fragments.extend(_string_fragments(argument))
        for keyword in node.keywords:
            call_fragments.extend(_string_fragments(keyword.value))
        return tuple(call_fragments)
    return ()


def _looks_machine_code(text: str) -> bool:
    stripped = text.strip()
    return bool(
        stripped
        and stripped.isascii()
        and stripped[0].isalpha()
        and stripped[0].islower()
        and all(
            character.islower()
            or character.isdigit()
            or character == "_"
            for character in stripped
        )
    )


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


__all__ = (
    "DeepSurfaceAudit",
    "augment_report_with_deep_literals",
    "collect_deep_literals",
)

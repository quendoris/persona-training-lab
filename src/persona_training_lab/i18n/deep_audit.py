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
    "SnapshotMetric": ((0, "title"), (2, "note")),
    "SnapshotRow": (
        (1, "title"),
        (2, "status"),
        (3, "subtitle"),
        (9, "quality_summary"),
    ),
    "TimelineItem": ((0, "title"), (1, "note")),
    "create_from_training_run": ((5, "quality_summary"),),
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
    "DatasetPreviewRecord": ((1, "input_summary"),),
    "OperationsCenterItem": (
        (1, "title"),
        (2, "summary"),
        (7, "focus_text"),
    ),
    "TraitView": ((0, "name"), (2, "note")),
    "ProfileView": ((9, "linked_artifacts"), (11, "readiness")),
    "TrainingConfigurationError": ((0, "message"),),
    "TrainingValidationError": ((0, "message"),),
}
_STRUCTURED_MACHINE_TEXT: dict[str, tuple[tuple[int, str], ...]] = {
    "DatasetDiagnostic": ((0, "code"),),
    "dataset_diagnostic": ((0, "code"),),
    "DatasetPreviewRecord": ((3, "quality"),),
    "DatasetServiceError": ((0, "code"),),
    "DatasetValidationResult": ((0, "status"),),
    "OperationsCenterItem": (
        (3, "status"),
        (4, "severity"),
        (6, "target_screen"),
        (9, "operation_kind"),
        (10, "operation_state"),
    ),
}
_MACHINE_CODE_CLASSES = frozenset(
    {
        "DatasetServiceErrorCode",
        "ProfileStatus",
    }
)
_TYPED_DATASET_ERROR_FUNCTIONS = frozenset(
    {
        "add_dataset_from_path",
        "approve_dataset",
        "validate_dataset",
    }
)
_FORBIDDEN_UI_PRESENTATION_CATALOGS = frozenset({"_LEGACY_TEMPLATES"})
_FORBIDDEN_OPERATIONS_PRESENTATION_FUNCTIONS = frozenset(
    {"_operation_label", "_state_label"}
)
_OPERATIONS_MACHINE_OR_KEY_RESULT_FUNCTIONS = frozenset(
    {"_operation_target", "_event_target"}
)
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
_UI_VIEWMODEL_RESULT_FUNCTIONS = frozenset(
    {
        "add_dataset_from_path",
        "approve_current_dataset",
        "compare_current_versions",
        "create_profile",
        "header_summary",
        "lineage",
        "next_step",
        "profiles",
        "right_summary",
        "update_current_profile",
        "validate_current_dataset",
    }
)
_PERSISTED_SEMANTIC_FIELDS = {
    "add_dataset_from_path": frozenset(
        {
            "subtitle",
            "status",
            "quality_summary",
            "validation_errors_preview",
            "readiness",
        }
    ),
    "add_dataset": frozenset(
        {
            "status",
            "quality_summary",
            "validation_errors_preview",
            "readiness",
        }
    ),
    "update_dataset_validation": frozenset(
        {"status", "quality_summary", "validation_errors_preview"}
    ),
    "_save_result": frozenset(
        {"status", "quality_summary", "validation_errors_preview"}
    ),
    "create_profile": frozenset({"status"}),
    "update_profile": frozenset({"status"}),
    "create_training_run": frozenset({"status"}),
    "start_full_finetune_run": frozenset({"status"}),
    "_set_terminal_error": frozenset({"status"}),
    "create_from_training_run": frozenset({"status", "quality_summary"}),
}
_MACHINE_RESULT_FUNCTIONS = frozenset({"_readiness_from_status"})
_USER_RESULT_FUNCTIONS = frozenset(
    {
        "approve_dataset",
        "compare_dataset_versions",
        "create_profile",
        "start_full_finetune_run",
        "update_profile",
    }
)
_OPAQUE_VALIDATED_CALLS = frozenset(
    {
        "ActionResult",
        "UserMessage",
        "DatasetDiagnostic",
        "dataset_diagnostic",
        "encode_dataset_diagnostic",
        "DatasetServiceError",
        "DatasetText",
        "dataset_text",
        "ProfileText",
        "profile_text",
        "TrainingText",
        "training_text",
        "EvaluationText",
        "evaluation_text",
        "SnapshotText",
        "snapshot_text",
    }
)


class DeepSurfaceAudit(ast.NodeVisitor):
    """Find source-language text hidden behind semantic/application surfaces.

    The ordinary source audit intentionally focuses on direct UI calls and
    explicitly modeled presentation DTOs. This second pass targets historical
    compatibility surfaces where text can still reach the UI without appearing
    in a QWidget call: application result objects, typed user-facing errors,
    legacy public fields and return values on UI view models, and persisted
    semantic fields that must remain language-neutral.

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
        self._is_operations_center_service = _is_operations_center_service_path(path)
        self.literals: list[LiteralFinding] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if (
            self._is_operations_center_service
            and node.name in _FORBIDDEN_OPERATIONS_PRESENTATION_FUNCTIONS
        ):
            self.literals.append(
                LiteralFinding(
                    path=_display_path(self._path, self._display_root),
                    line=getattr(node, "lineno", 0),
                    call="forbidden operations presentation helper",
                    text=node.name,
                )
            )
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
        if (
            self._class_stack
            and not self._function_stack
            and self._class_stack[-1] in _MACHINE_CODE_CLASSES
        ):
            machine_fragments = tuple(
                fragment
                for fragment in fragments
                if not _looks_machine_code(fragment)
            )
            self._append_fragments(
                node,
                f"{self._class_stack[-1]} code",
                machine_fragments,
            )
        if self._is_ui_viewmodel:
            for target in node.targets:
                if (
                    not self._function_stack
                    and isinstance(target, ast.Name)
                    and target.id in _FORBIDDEN_UI_PRESENTATION_CATALOGS
                ):
                    self.literals.append(
                        LiteralFinding(
                            path=_display_path(
                                self._path,
                                self._display_root,
                            ),
                            line=getattr(node, "lineno", 0),
                            call="forbidden presentation catalog",
                            text=target.id,
                        )
                    )
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
        if (
            self._class_stack
            and not self._function_stack
            and self._class_stack[-1] in _MACHINE_CODE_CLASSES
        ):
            machine_fragments = tuple(
                fragment
                for fragment in fragments
                if not _looks_machine_code(fragment)
            )
            self._append_fragments(
                node,
                f"{self._class_stack[-1]} code",
                machine_fragments,
            )
        if self._is_ui_viewmodel:
            if (
                not self._function_stack
                and isinstance(node.target, ast.Name)
                and node.target.id in _FORBIDDEN_UI_PRESENTATION_CATALOGS
            ):
                self.literals.append(
                    LiteralFinding(
                        path=_display_path(self._path, self._display_root),
                        line=getattr(node, "lineno", 0),
                        call="forbidden presentation catalog",
                        text=node.target.id,
                    )
                )
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
        if (
            self._is_operations_center_service
            and function_name in _OPERATIONS_MACHINE_OR_KEY_RESULT_FUNCTIONS
        ):
            for value in node.values:
                fragments = tuple(
                    fragment
                    for fragment in self._resolved_fragments(value)
                    if not _looks_machine_code(fragment)
                    and not _looks_translation_key(fragment)
                )
                self._append_fragments(
                    node,
                    f"{function_name} mapping",
                    fragments,
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node.func)
        function_name = self._function_stack[-1] if self._function_stack else ""
        persisted_fields = _PERSISTED_SEMANTIC_FIELDS.get(function_name)
        if (
            call_name == "get"
            and persisted_fields is not None
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value in persisted_fields
        ):
            field = node.args[0].value
            fragments = tuple(
                fragment
                for fragment in self._resolved_fragments(node.args[1])
                if not _looks_machine_code(fragment)
            )
            self._append_fragments(
                node,
                f"{function_name} persisted {field} default",
                fragments,
            )
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
        machine_structured = _STRUCTURED_MACHINE_TEXT.get(call_name)
        if machine_structured is not None:
            for position, keyword in machine_structured:
                expression = _argument_expression(
                    node,
                    position,
                    keyword=keyword,
                )
                if expression is None:
                    continue
                fragments = tuple(
                    fragment
                    for fragment in self._resolved_fragments(expression)
                    if not _looks_machine_code(fragment)
                )
                self._append_fragments(
                    node,
                    f"{call_name} {keyword}",
                    fragments,
                )
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        function_name = self._function_stack[-1] if self._function_stack else ""
        if (
            node.exc is not None
            and self._class_stack
            and self._class_stack[-1] == "DatasetsService"
            and function_name in _TYPED_DATASET_ERROR_FUNCTIONS
            and not (
                isinstance(node.exc, ast.Call)
                and _call_name(node.exc.func) == "DatasetServiceError"
            )
        ):
            self.literals.append(
                LiteralFinding(
                    path=_display_path(self._path, self._display_root),
                    line=getattr(node, "lineno", 0),
                    call=f"{function_name} exception protocol",
                    text=_exception_expression_name(node.exc),
                )
            )
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        function_name = self._function_stack[-1] if self._function_stack else ""
        if (
            node.value is not None
            and self._is_operations_center_service
            and function_name in _OPERATIONS_MACHINE_OR_KEY_RESULT_FUNCTIONS
        ):
            fragments = tuple(
                fragment
                for fragment in self._resolved_fragments(node.value)
                if not _looks_machine_code(fragment)
                and not _looks_translation_key(fragment)
            )
            self._append_fragments(
                node,
                f"{function_name} return",
                fragments,
            )
        elif node.value is not None and function_name in _MACHINE_RESULT_FUNCTIONS:
            fragments = tuple(
                fragment
                for fragment in self._resolved_fragments(node.value)
                if not _looks_machine_code(fragment)
            )
            self._append_fragments(
                node,
                f"{function_name} return",
                fragments,
            )
        elif node.value is not None and (
            function_name in _USER_RESULT_FUNCTIONS
            or (
                self._is_ui_viewmodel
                and function_name in _UI_VIEWMODEL_RESULT_FUNCTIONS
            )
        ):
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


def _is_operations_center_service_path(path: Path) -> bool:
    parts = path.parts
    return (
        path.name == "service.py"
        and "operations_center" in parts
        and "application" in parts
    )


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


def _exception_expression_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        return _call_name(node.func) or type(node.func).__name__
    if isinstance(node, ast.Name):
        return node.id
    return type(node).__name__


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


def _looks_translation_key(text: str) -> bool:
    stripped = text.strip()
    return bool(
        "." in stripped
        and stripped.isascii()
        and all(
            character.islower()
            or character.isdigit()
            or character in {"_", "."}
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
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import os
import sys
from types import MappingProxyType
from typing import Mapping, Protocol

from persona_training_lab.application.automation.audit import AutomationAuditTrail
from persona_training_lab.application.automation.execution import (
    DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES,
    AutomationEffectScope,
    AutomationExecution,
    AutomationExecutionMode,
    AutomationProcessResult,
    AutomationProcessRunner,
    run_automation_process,
)
from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
    RuntimeOperationCoordinator,
)


AUTOMATION_RECIPE_SCHEMA = "ptl:automation-recipe:v1"


@dataclass(frozen=True, slots=True)
class AutomationInput:
    name: str
    required: bool = False
    default: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class AutomationOutput:
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class AutomationResourceClaim:
    resource_kind: str
    resource_id: str
    access_mode: str = "read"


@dataclass(frozen=True, slots=True)
class AutomationRecipe:
    recipe_id: str
    version: str
    title: str
    description: str
    command: tuple[str, ...]
    tags: tuple[str, ...] = ()
    inputs: tuple[AutomationInput, ...] = ()
    outputs: tuple[AutomationOutput, ...] = ()
    resource_claims: tuple[AutomationResourceClaim, ...] = ()
    source: str = "workspace"
    source_path: str = ""
    working_directory: str = ""
    timeout_seconds: int = 0


@dataclass(frozen=True, slots=True)
class AutomationCommandRequest:
    command_id: str
    mode: AutomationExecutionMode = "exec"
    argv: tuple[str, ...] = ()
    shell_command: str = ""
    working_directory: str = ""
    environment: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    inherit_environment: bool = True
    resource_claims: tuple[AutomationResourceClaim, ...] = ()
    timeout_seconds: float = 0.0
    output_limit_bytes: int = DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES
    host_effects_authorized: bool = False


@dataclass(frozen=True, slots=True)
class AutomationDiscoveryIssue:
    path: str
    code: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class AutomationRunResult:
    ok: bool
    code: str
    recipe_id: str
    operation_id: str = ""
    return_code: int | None = None
    execution_mode: AutomationExecutionMode = "exec"
    effect_scope: AutomationEffectScope = "trusted_host"
    command: tuple[str, ...] = ()
    working_directory: str = ""
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    values: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({})
    )


class AutomationRecipeProvider(Protocol):
    def list_recipes(self) -> tuple[AutomationRecipe, ...]: ...

    def discovery_issues(self) -> tuple[AutomationDiscoveryIssue, ...]: ...

    def import_recipe(self, path: Path) -> AutomationRecipe: ...


@dataclass(slots=True)
class AutomationService:
    recipe_provider: AutomationRecipeProvider
    operation_coordinator: RuntimeOperationCoordinator
    workspace_root: Path
    process_runner: AutomationProcessRunner = run_automation_process
    audit_trail: AutomationAuditTrail | None = None

    def list_recipes(self, query: str = "") -> tuple[AutomationRecipe, ...]:
        recipes = tuple(self.recipe_provider.list_recipes())
        needle = query.strip().casefold()
        if needle:
            recipes = tuple(
                recipe
                for recipe in recipes
                if needle in recipe.recipe_id.casefold()
                or needle in recipe.title.casefold()
                or needle in recipe.description.casefold()
                or any(needle in tag.casefold() for tag in recipe.tags)
            )
        return tuple(
            sorted(
                recipes,
                key=lambda recipe: (recipe.title.casefold(), recipe.recipe_id),
            )
        )

    def discovery_issues(self) -> tuple[AutomationDiscoveryIssue, ...]:
        self.recipe_provider.list_recipes()
        return self.recipe_provider.discovery_issues()

    def get_recipe(self, recipe_id: str) -> AutomationRecipe | None:
        target = recipe_id.strip()
        return next(
            (
                recipe
                for recipe in self.recipe_provider.list_recipes()
                if recipe.recipe_id == target
            ),
            None,
        )

    def import_recipe(self, path: Path) -> AutomationRecipe:
        return self.recipe_provider.import_recipe(path)

    def run_recipe(
        self,
        recipe_id: str,
        inputs: Mapping[str, str] | None = None,
        *,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> AutomationRunResult:
        recipe = self.get_recipe(recipe_id)
        if recipe is None:
            return AutomationRunResult(False, "recipe_not_found", recipe_id.strip())

        supplied = {
            str(key).strip(): str(value)
            for key, value in (inputs or {}).items()
            if str(key).strip()
        }
        declared = {item.name: item for item in recipe.inputs}
        unknown = sorted(set(supplied) - set(declared))
        if unknown:
            return AutomationRunResult(
                False,
                "input_unknown",
                recipe.recipe_id,
                values=MappingProxyType({"inputs": tuple(unknown)}),
            )

        resolved: dict[str, str] = {
            name: item.default for name, item in declared.items()
        }
        resolved.update(supplied)
        missing = tuple(
            name
            for name, item in declared.items()
            if item.required and not resolved.get(name, "").strip()
        )
        if missing:
            return AutomationRunResult(
                False,
                "input_required",
                recipe.recipe_id,
                values=MappingProxyType({"inputs": missing}),
            )

        substitutions = {
            **resolved,
            "python": sys.executable,
            "workspace": str(self.workspace_root.resolve()),
        }
        try:
            command = tuple(
                self._render_token(token, substitutions) for token in recipe.command
            )
            claims = tuple(
                ResourceClaim(
                    claim.resource_kind,
                    self._render_token(claim.resource_id, substitutions),
                    claim.access_mode,
                )
                for claim in recipe.resource_claims
            )
            cwd = self._working_directory(recipe, substitutions)
            execution = AutomationExecution(
                mode="exec",
                argv=command,
                cwd=cwd,
                env=self._environment_snapshot(),
                timeout=(
                    float(recipe.timeout_seconds)
                    if recipe.timeout_seconds > 0
                    else None
                ),
            )
        except (KeyError, ValueError) as exc:
            return AutomationRunResult(
                False,
                "recipe_invalid",
                recipe.recipe_id,
                stderr=str(exc),
            )

        return self._execute(
            result_id=recipe.recipe_id,
            execution=execution,
            operation_kind="automation_recipe",
            subject_kind="automation_recipe",
            claims=claims,
            cancel_requested=cancel_requested,
        )

    def run_command(
        self,
        request: AutomationCommandRequest,
        *,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> AutomationRunResult:
        command_id = request.command_id.strip() or "ad_hoc"
        if not request.host_effects_authorized:
            return AutomationRunResult(
                False,
                "host_effects_not_authorized",
                command_id,
                execution_mode=request.mode,
            )
        try:
            claims = tuple(
                ResourceClaim(
                    claim.resource_kind,
                    claim.resource_id,
                    claim.access_mode,
                )
                for claim in request.resource_claims
            )
            if not claims:
                claims = (
                    ResourceClaim(
                        "workspace",
                        str(self.workspace_root.resolve()),
                        "write",
                    ),
                )
            execution = AutomationExecution(
                mode=request.mode,
                argv=tuple(request.argv),
                shell_command=request.shell_command,
                cwd=self._command_working_directory(request.working_directory),
                env=self._environment_snapshot(
                    request.environment,
                    inherit=request.inherit_environment,
                ),
                timeout=(
                    float(request.timeout_seconds)
                    if request.timeout_seconds > 0
                    else None
                ),
                output_limit_bytes=request.output_limit_bytes,
            )
        except ValueError:
            return AutomationRunResult(
                False,
                "command_invalid",
                command_id,
                execution_mode=request.mode,
            )

        if self.audit_trail is None:
            return AutomationRunResult(
                False,
                "audit_unavailable",
                command_id,
                execution_mode=execution.mode,
                effect_scope=execution.effect_scope,
                command=execution.command_snapshot,
                working_directory=str(execution.cwd),
            )

        return self._execute(
            result_id=command_id,
            execution=execution,
            operation_kind="automation_command",
            subject_kind="automation_command",
            claims=claims,
            cancel_requested=cancel_requested,
        )

    def _execute(
        self,
        *,
        result_id: str,
        execution: AutomationExecution,
        operation_kind: str,
        subject_kind: str,
        claims: tuple[ResourceClaim, ...],
        cancel_requested: Callable[[], bool] | None,
    ) -> AutomationRunResult:
        command = execution.command_snapshot
        cwd = str(execution.cwd)
        try:
            lease = self.operation_coordinator.begin(
                operation_kind=operation_kind,
                subject_kind=subject_kind,
                subject_id=result_id,
                claims=claims,
            )
        except OperationConflictError as exc:
            if self.audit_trail is not None:
                try:
                    self.audit_trail.record_blocked(
                        operation_kind=operation_kind,
                        subject_kind=subject_kind,
                        subject_id=result_id,
                        execution=execution,
                        claims=claims,
                        detail=str(exc),
                    )
                except Exception as audit_exc:
                    return AutomationRunResult(
                        False,
                        "audit_failed",
                        result_id,
                        execution_mode=execution.mode,
                        effect_scope=execution.effect_scope,
                        command=command,
                        working_directory=cwd,
                        stderr=str(audit_exc),
                    )
            return AutomationRunResult(
                False,
                "operation_blocked",
                result_id,
                execution_mode=execution.mode,
                effect_scope=execution.effect_scope,
                command=command,
                working_directory=cwd,
                stderr=str(exc),
            )

        with lease:
            if self.audit_trail is not None:
                try:
                    self.audit_trail.record_started(
                        operation_id=lease.operation_id,
                        correlation_id=lease.correlation_id,
                        operation_kind=operation_kind,
                        subject_kind=subject_kind,
                        subject_id=result_id,
                        execution=execution,
                        claims=claims,
                    )
                except Exception as exc:
                    lease.fail(f"automation audit start failed: {exc}")
                    return AutomationRunResult(
                        False,
                        "audit_failed",
                        result_id,
                        operation_id=lease.operation_id,
                        execution_mode=execution.mode,
                        effect_scope=execution.effect_scope,
                        command=command,
                        working_directory=cwd,
                        stderr=str(exc),
                    )

            try:
                completed: AutomationProcessResult = self.process_runner(
                    execution,
                    cancel_requested=cancel_requested,
                )
            except (OSError, RuntimeError) as exc:
                if self.audit_trail is not None:
                    try:
                        self.audit_trail.record_launch_failed(
                            operation_id=lease.operation_id,
                            correlation_id=lease.correlation_id,
                            operation_kind=operation_kind,
                            subject_kind=subject_kind,
                            subject_id=result_id,
                            execution=execution,
                            claims=claims,
                            detail=str(exc),
                        )
                    except Exception as audit_exc:
                        lease.fail(f"automation audit finish failed: {audit_exc}")
                        return AutomationRunResult(
                            False,
                            "audit_failed",
                            result_id,
                            operation_id=lease.operation_id,
                            execution_mode=execution.mode,
                            effect_scope=execution.effect_scope,
                            command=command,
                            working_directory=cwd,
                            stderr=str(audit_exc),
                        )
                lease.fail(str(exc))
                return AutomationRunResult(
                    False,
                    "launch_failed",
                    result_id,
                    operation_id=lease.operation_id,
                    execution_mode=execution.mode,
                    effect_scope=execution.effect_scope,
                    command=command,
                    working_directory=cwd,
                    stderr=str(exc),
                )

            if completed.cancelled:
                code = "cancelled"
                ok = False
                state = "cancelled"
            elif completed.timed_out:
                code = "timeout"
                ok = False
                state = "failed"
            elif completed.return_code == 0:
                code = "succeeded"
                ok = True
                state = "succeeded"
            else:
                code = "failed"
                ok = False
                state = "failed"

            if self.audit_trail is not None:
                try:
                    self.audit_trail.record_finished(
                        operation_id=lease.operation_id,
                        correlation_id=lease.correlation_id,
                        operation_kind=operation_kind,
                        subject_kind=subject_kind,
                        subject_id=result_id,
                        execution=execution,
                        claims=claims,
                        result=completed,
                        state=state,
                    )
                except Exception as exc:
                    lease.fail(f"automation audit finish failed: {exc}")
                    return AutomationRunResult(
                        False,
                        "audit_failed",
                        result_id,
                        operation_id=lease.operation_id,
                        return_code=completed.return_code,
                        execution_mode=execution.mode,
                        effect_scope=execution.effect_scope,
                        command=command,
                        working_directory=cwd,
                        stdout=completed.stdout,
                        stderr=completed.stderr or str(exc),
                        stdout_truncated=completed.stdout_truncated,
                        stderr_truncated=completed.stderr_truncated,
                    )

            if state == "cancelled":
                lease.cancel("cancelled")
            elif state == "succeeded":
                lease.succeed()
            elif completed.timed_out:
                lease.fail("timeout")
            else:
                lease.fail(completed.stderr or f"exit {completed.return_code}")

            return AutomationRunResult(
                ok,
                code,
                result_id,
                operation_id=lease.operation_id,
                return_code=completed.return_code,
                execution_mode=execution.mode,
                effect_scope=execution.effect_scope,
                command=command,
                working_directory=cwd,
                stdout=completed.stdout,
                stderr=completed.stderr,
                stdout_truncated=completed.stdout_truncated,
                stderr_truncated=completed.stderr_truncated,
            )

    def _environment_snapshot(
        self,
        overrides: Mapping[str, str] | None = None,
        *,
        inherit: bool = True,
    ) -> Mapping[str, str]:
        environment = dict(os.environ) if inherit else {}
        environment.update(
            {str(key): str(value) for key, value in (overrides or {}).items()}
        )
        environment["PTL_WORKSPACE"] = str(self.workspace_root.resolve())
        return MappingProxyType(environment)

    def _command_working_directory(self, value: str) -> Path:
        if not value.strip():
            return self.workspace_root.resolve()
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.workspace_root.resolve() / path
        return path.resolve()

    def _working_directory(
        self,
        recipe: AutomationRecipe,
        substitutions: Mapping[str, str],
    ) -> Path:
        if not recipe.working_directory:
            return self.workspace_root.resolve()
        rendered = self._render_token(recipe.working_directory, substitutions)
        path = Path(rendered).expanduser()
        if not path.is_absolute():
            source_parent = (
                Path(recipe.source_path).resolve().parent
                if recipe.source_path
                else self.workspace_root.resolve()
            )
            path = source_parent / path
        return path.resolve()

    @staticmethod
    def _render_token(token: str, substitutions: Mapping[str, str]) -> str:
        try:
            return token.format_map(substitutions)
        except KeyError as exc:
            raise KeyError(f"unknown recipe placeholder: {exc.args[0]}") from exc

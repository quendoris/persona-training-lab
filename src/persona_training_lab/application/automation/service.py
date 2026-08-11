from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import subprocess
import sys
from types import MappingProxyType
from typing import Mapping, Protocol, Sequence

from persona_training_lab.application.runtime.operations import (
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
    title_key: str = ""
    description_key: str = ""


@dataclass(frozen=True, slots=True)
class AutomationRunResult:
    ok: bool
    code: str
    recipe_id: str
    operation_id: str = ""
    return_code: int | None = None
    command: tuple[str, ...] = ()
    stdout: str = ""
    stderr: str = ""
    values: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({})
    )


class AutomationRecipeProvider(Protocol):
    def list_recipes(self) -> tuple[AutomationRecipe, ...]: ...

    def import_recipe(self, path: Path) -> AutomationRecipe: ...


class AutomationProcessRunner(Protocol):
    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout: float | None,
    ) -> subprocess.CompletedProcess[str]: ...


def _default_runner(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout: float | None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        tuple(command),
        cwd=cwd,
        env=dict(env),
        timeout=timeout,
        check=False,
        capture_output=True,
        text=True,
    )


@dataclass(slots=True)
class AutomationService:
    recipe_provider: AutomationRecipeProvider
    operation_coordinator: RuntimeOperationCoordinator
    workspace_root: Path
    process_runner: AutomationProcessRunner = _default_runner

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
        except (KeyError, ValueError) as exc:
            return AutomationRunResult(
                False,
                "recipe_invalid",
                recipe.recipe_id,
                stderr=str(exc),
            )

        if not command:
            return AutomationRunResult(
                False,
                "recipe_invalid",
                recipe.recipe_id,
                stderr="empty command",
            )

        environment = dict(os.environ)
        environment["PTL_WORKSPACE"] = str(self.workspace_root.resolve())
        timeout = float(recipe.timeout_seconds) if recipe.timeout_seconds > 0 else None

        try:
            with self.operation_coordinator.begin(
                operation_kind="automation_recipe",
                subject_kind="automation_recipe",
                subject_id=recipe.recipe_id,
                claims=claims,
            ) as lease:
                try:
                    completed = self.process_runner(
                        command,
                        cwd=cwd,
                        env=environment,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired as exc:
                    lease.fail("timeout")
                    return AutomationRunResult(
                        False,
                        "timeout",
                        recipe.recipe_id,
                        operation_id=lease.operation_id,
                        command=command,
                        stdout=self._text(exc.stdout),
                        stderr=self._text(exc.stderr),
                    )
                except OSError as exc:
                    lease.fail(str(exc))
                    return AutomationRunResult(
                        False,
                        "launch_failed",
                        recipe.recipe_id,
                        operation_id=lease.operation_id,
                        command=command,
                        stderr=str(exc),
                    )

                if completed.returncode == 0:
                    lease.succeed()
                    code = "succeeded"
                    ok = True
                else:
                    lease.fail(completed.stderr or f"exit {completed.returncode}")
                    code = "failed"
                    ok = False
                return AutomationRunResult(
                    ok,
                    code,
                    recipe.recipe_id,
                    operation_id=lease.operation_id,
                    return_code=completed.returncode,
                    command=command,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )
        except Exception as exc:
            return AutomationRunResult(
                False,
                "operation_blocked",
                recipe.recipe_id,
                command=command,
                stderr=str(exc),
            )

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

    @staticmethod
    def _text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

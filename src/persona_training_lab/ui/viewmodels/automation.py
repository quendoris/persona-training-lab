from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from persona_training_lab.application.automation import (
    AutomationDiscoveryIssue,
    AutomationRecipe,
    AutomationRunResult,
    AutomationService,
)


AUTOMATION_RECIPE_TITLE_KEYS = {
    "workspace_health": "automation.recipe.workspace_health.title",
}
AUTOMATION_RECIPE_DESCRIPTION_KEYS = {
    "workspace_health": "automation.recipe.workspace_health.description",
}
AUTOMATION_RUN_STATUS_KEYS = {
    "succeeded": "automation.run.status.succeeded",
    "failed": "automation.run.status.failed",
    "cancelled": "automation.run.status.cancelled",
    "timeout": "automation.run.status.timeout",
    "launch_failed": "automation.run.status.launch_failed",
    "operation_blocked": "automation.run.status.operation_blocked",
    "recipe_not_found": "automation.run.status.recipe_not_found",
    "recipe_invalid": "automation.run.status.recipe_invalid",
    "input_required": "automation.run.status.input_required",
    "input_unknown": "automation.run.status.input_unknown",
}
AUTOMATION_DISCOVERY_ISSUE_KEYS = {
    "manifest_invalid": "automation.discovery.manifest_invalid",
    "recipe_duplicate": "automation.discovery.recipe_duplicate",
}


@dataclass(frozen=True, slots=True)
class AutomationText:
    key: str
    values: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({})
    )


AutomationTextValue = str | AutomationText


@dataclass(frozen=True, slots=True)
class AutomationRecipeView:
    recipe_id: str
    version: str
    title: AutomationTextValue
    description: AutomationTextValue
    tags: tuple[str, ...]
    command: str
    source: str
    source_path: str
    inputs: tuple[tuple[str, bool, str, str], ...]
    outputs: tuple[tuple[str, str], ...]
    resources: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True, slots=True)
class AutomationIssueView:
    path: str
    message: AutomationText
    detail: str


@dataclass(frozen=True, slots=True)
class AutomationRunView:
    ok: bool
    status: AutomationText
    recipe_id: str
    operation_id: str
    return_code: int | None
    command: str
    stdout: str
    stderr: str


def automation_text(key: str, **values: object) -> AutomationText:
    return AutomationText(key, MappingProxyType(dict(values)))


@dataclass(slots=True)
class AutomationViewModel:
    automation_service: AutomationService

    def recipes(self, query: str = "") -> tuple[AutomationRecipeView, ...]:
        return tuple(
            self._recipe_view(recipe)
            for recipe in self.automation_service.list_recipes(query)
        )

    def discovery_issues(self) -> tuple[AutomationIssueView, ...]:
        return tuple(
            self._issue_view(issue)
            for issue in self.automation_service.discovery_issues()
        )

    def import_recipe(self, path: Path) -> AutomationRecipeView:
        return self._recipe_view(self.automation_service.import_recipe(path))

    def run_recipe(
        self,
        recipe_id: str,
        inputs: Mapping[str, str] | None = None,
        *,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> AutomationRunView:
        return self._run_view(
            self.automation_service.run_recipe(
                recipe_id,
                inputs,
                cancel_requested=cancel_requested,
            )
        )

    @staticmethod
    def _recipe_view(recipe: AutomationRecipe) -> AutomationRecipeView:
        title_key = AUTOMATION_RECIPE_TITLE_KEYS.get(recipe.recipe_id)
        description_key = AUTOMATION_RECIPE_DESCRIPTION_KEYS.get(recipe.recipe_id)
        title: AutomationTextValue = (
            automation_text(title_key) if title_key else recipe.title
        )
        description: AutomationTextValue = (
            automation_text(description_key)
            if description_key
            else recipe.description
        )
        return AutomationRecipeView(
            recipe_id=recipe.recipe_id,
            version=recipe.version,
            title=title,
            description=description,
            tags=recipe.tags,
            command=" ".join(recipe.command),
            source=recipe.source,
            source_path=recipe.source_path,
            inputs=tuple(
                (item.name, item.required, item.default, item.description)
                for item in recipe.inputs
            ),
            outputs=tuple(
                (item.name, item.description) for item in recipe.outputs
            ),
            resources=tuple(
                (claim.resource_kind, claim.resource_id, claim.access_mode)
                for claim in recipe.resource_claims
            ),
        )

    @staticmethod
    def _issue_view(issue: AutomationDiscoveryIssue) -> AutomationIssueView:
        key = AUTOMATION_DISCOVERY_ISSUE_KEYS.get(
            issue.code,
            "automation.discovery.unknown",
        )
        return AutomationIssueView(
            path=issue.path,
            message=automation_text(key),
            detail=issue.detail,
        )

    @staticmethod
    def _run_view(result: AutomationRunResult) -> AutomationRunView:
        key = AUTOMATION_RUN_STATUS_KEYS.get(
            result.code,
            "automation.run.status.unknown",
        )
        values: dict[str, object] = {}
        inputs = result.values.get("inputs")
        if isinstance(inputs, tuple):
            values["inputs"] = ", ".join(str(item) for item in inputs)
        return AutomationRunView(
            ok=result.ok,
            status=automation_text(key, **values),
            recipe_id=result.recipe_id,
            operation_id=result.operation_id,
            return_code=result.return_code,
            command=" ".join(result.command),
            stdout=result.stdout,
            stderr=result.stderr,
        )

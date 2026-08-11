from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
from typing import Any

from persona_training_lab.application.automation.service import (
    AUTOMATION_RECIPE_SCHEMA,
    AutomationDiscoveryIssue,
    AutomationInput,
    AutomationOutput,
    AutomationRecipe,
    AutomationResourceClaim,
)


_RECIPE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_INPUT_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RECIPE_GLOB = "*.ptl-recipe.json"
_VALID_ACCESS_MODES = frozenset({"read", "write"})


class FilesystemAutomationRecipeProvider:
    def __init__(self, registry_dir: Path) -> None:
        self._registry_dir = registry_dir
        self._registry_dir.mkdir(parents=True, exist_ok=True)
        self._issues: tuple[AutomationDiscoveryIssue, ...] = ()

    @property
    def registry_dir(self) -> Path:
        return self._registry_dir

    def list_recipes(self) -> tuple[AutomationRecipe, ...]:
        recipes: dict[str, AutomationRecipe] = {
            recipe.recipe_id: recipe for recipe in self._builtin_recipes()
        }
        issues: list[AutomationDiscoveryIssue] = []
        for path in sorted(self._registry_dir.rglob(_RECIPE_GLOB)):
            try:
                recipe = self._load_manifest(path)
            except Exception as exc:
                issues.append(
                    AutomationDiscoveryIssue(
                        str(path),
                        "manifest_invalid",
                        str(exc),
                    )
                )
                continue
            if recipe.recipe_id in recipes:
                issues.append(
                    AutomationDiscoveryIssue(
                        str(path),
                        "recipe_duplicate",
                        recipe.recipe_id,
                    )
                )
                continue
            recipes[recipe.recipe_id] = recipe
        self._issues = tuple(issues)
        return tuple(recipes.values())

    def discovery_issues(self) -> tuple[AutomationDiscoveryIssue, ...]:
        return self._issues

    def import_recipe(self, path: Path) -> AutomationRecipe:
        source = path.expanduser().resolve()
        recipe = self._load_manifest(source)
        target = self._registry_dir / f"{recipe.recipe_id}.ptl-recipe.json"
        if source != target.resolve():
            shutil.copy2(source, target)
        imported = self._load_manifest(target)
        self.list_recipes()
        return imported

    def _load_manifest(self, path: Path) -> AutomationRecipe:
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("recipe manifest root must be an object")
        if payload.get("schema") != AUTOMATION_RECIPE_SCHEMA:
            raise ValueError("unsupported recipe schema")

        recipe_id = self._required_text(payload, "id").casefold()
        if _RECIPE_ID_RE.fullmatch(recipe_id) is None:
            raise ValueError("recipe id must match [a-z0-9][a-z0-9._-]*")
        version = self._required_text(payload, "version")
        title = str(payload.get("title") or recipe_id).strip() or recipe_id
        description = str(payload.get("description") or "").strip()
        command = self._string_tuple(payload.get("command"), required=True)
        tags = tuple(
            dict.fromkeys(
                item.casefold() for item in self._string_tuple(payload.get("tags"))
            )
        )
        inputs = self._inputs(payload.get("inputs"))
        outputs = self._outputs(payload.get("outputs"))
        claims = self._claims(payload.get("resources"))
        timeout = self._nonnegative_int(payload.get("timeout_seconds", 0))

        return AutomationRecipe(
            recipe_id=recipe_id,
            version=version,
            title=title,
            description=description,
            command=command,
            tags=tags,
            inputs=inputs,
            outputs=outputs,
            resource_claims=claims,
            source="workspace",
            source_path=str(path.resolve()),
            working_directory=str(payload.get("working_directory") or "").strip(),
            timeout_seconds=timeout,
        )

    @staticmethod
    def _builtin_recipes() -> tuple[AutomationRecipe, ...]:
        return (
            AutomationRecipe(
                recipe_id="workspace_health",
                version="1.0.0",
                title="workspace_health",
                description="",
                command=(
                    "{python}",
                    "-m",
                    "persona_training_lab.automation_recipes.workspace_health",
                ),
                tags=("diagnostic", "workspace"),
                outputs=(AutomationOutput("stdout_json"),),
                resource_claims=(
                    AutomationResourceClaim("workspace", "{workspace}", "read"),
                ),
                source="builtin",
            ),
        )

    @staticmethod
    def _required_text(payload: dict[str, Any], key: str) -> str:
        value = str(payload.get(key) or "").strip()
        if not value:
            raise ValueError(f"recipe field {key!r} must not be empty")
        return value

    @staticmethod
    def _string_tuple(value: Any, *, required: bool = False) -> tuple[str, ...]:
        if value is None:
            if required:
                raise ValueError("recipe command must be a non-empty array")
            return ()
        if not isinstance(value, list):
            raise ValueError("recipe array field must be an array")
        result = tuple(str(item).strip() for item in value if str(item).strip())
        if required and not result:
            raise ValueError("recipe command must be a non-empty array")
        return result

    @classmethod
    def _inputs(cls, value: Any) -> tuple[AutomationInput, ...]:
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ValueError("recipe inputs must be an array")
        items: list[AutomationInput] = []
        names: set[str] = set()
        for raw in value:
            if not isinstance(raw, dict):
                raise ValueError("recipe input must be an object")
            name = cls._required_text(raw, "name")
            if _INPUT_NAME_RE.fullmatch(name) is None:
                raise ValueError(
                    "recipe input name must match [A-Za-z_][A-Za-z0-9_]*"
                )
            if name in {"python", "workspace"}:
                raise ValueError(f"reserved recipe input name: {name}")
            if name in names:
                raise ValueError(f"duplicate recipe input: {name}")
            names.add(name)
            items.append(
                AutomationInput(
                    name=name,
                    required=bool(raw.get("required", False)),
                    default=str(raw.get("default") or ""),
                    description=str(raw.get("description") or "").strip(),
                )
            )
        return tuple(items)

    @classmethod
    def _outputs(cls, value: Any) -> tuple[AutomationOutput, ...]:
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ValueError("recipe outputs must be an array")
        outputs: list[AutomationOutput] = []
        for raw in value:
            if not isinstance(raw, dict):
                raise ValueError("recipe output must be an object")
            outputs.append(
                AutomationOutput(
                    name=cls._required_text(raw, "name"),
                    description=str(raw.get("description") or "").strip(),
                )
            )
        return tuple(outputs)

    @classmethod
    def _claims(cls, value: Any) -> tuple[AutomationResourceClaim, ...]:
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ValueError("recipe resources must be an array")
        claims: list[AutomationResourceClaim] = []
        for raw in value:
            if not isinstance(raw, dict):
                raise ValueError("recipe resource must be an object")
            access = str(raw.get("access") or "read").strip().casefold()
            if access not in _VALID_ACCESS_MODES:
                raise ValueError(f"unsupported recipe resource access mode: {access}")
            claims.append(
                AutomationResourceClaim(
                    resource_kind=cls._required_text(raw, "kind"),
                    resource_id=cls._required_text(raw, "id"),
                    access_mode=access,
                )
            )
        return tuple(claims)

    @staticmethod
    def _nonnegative_int(value: Any) -> int:
        try:
            result = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("timeout_seconds must be an integer") from exc
        if result < 0:
            raise ValueError("timeout_seconds must be non-negative")
        return result

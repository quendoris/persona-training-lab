from __future__ import annotations

import json
from pathlib import Path
import re
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
            registered_ids = {item.recipe_id for item in self.list_recipes()}
            if recipe.recipe_id in registered_ids:
                raise FileExistsError(
                    f"recipe id already exists: {recipe.recipe_id}"
                )
            source_text = source.read_text(encoding="utf-8")
            try:
                with target.open("x", encoding="utf-8", newline="") as handle:
                    handle.write(source_text)
                    handle.flush()
            except Exception:
                try:
                    target.unlink(missing_ok=True)
                except OSError:
                    pass
                raise
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
        def action(
            recipe_id: str,
            title: str,
            description: str,
            action_id: str,
            *,
            inputs: tuple[AutomationInput, ...] = (),
            tags: tuple[str, ...] = (),
        ) -> AutomationRecipe:
            return AutomationRecipe(
                recipe_id=recipe_id,
                version="1.0.0",
                title=title,
                description=description,
                command=("ptl-action", action_id),
                tags=("ptl", "internal", *tags),
                inputs=inputs,
                outputs=(AutomationOutput("stdout_json"),),
                resource_claims=(
                    AutomationResourceClaim(
                        "automation_action",
                        recipe_id,
                        "write",
                    ),
                ),
                source="builtin",
                internal_action=action_id,
            )

        return (
            AutomationRecipe(
                recipe_id="workspace_health",
                version="1.0.0",
                title="",
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
            action(
                "ptl.model.probe",
                "PTL · Model probe",
                "Check model files and Transformers runtime compatibility.",
                "model.probe",
                inputs=(
                    AutomationInput(
                        "model_path",
                        default="Qwen3.5-0.8B",
                        description="Model reference or local path.",
                    ),
                ),
                tags=("model", "diagnostic"),
            ),
            action(
                "ptl.model.generate",
                "PTL · Model generate",
                "Run one text generation through the configured local model.",
                "model.generate",
                inputs=(
                    AutomationInput(
                        "model_path",
                        default="Qwen3.5-0.8B",
                        description="Model reference or local path.",
                    ),
                    AutomationInput(
                        "prompt",
                        required=True,
                        description="User prompt.",
                    ),
                    AutomationInput(
                        "instruction",
                        description="Optional system instruction.",
                    ),
                ),
                tags=("model", "inference"),
            ),
            action(
                "ptl.profile.create",
                "PTL · Create profile",
                "Create a Profile through ProfilesService.",
                "profile.create",
                inputs=(
                    AutomationInput("title", required=True),
                    AutomationInput("description", required=True),
                    AutomationInput(
                        "communication_style",
                        required=True,
                    ),
                    AutomationInput("principles", required=True),
                    AutomationInput("constraints", required=True),
                    AutomationInput("notes"),
                ),
                tags=("profile", "write"),
            ),
            action(
                "ptl.dataset.import",
                "PTL · Import dataset",
                "Import an external JSONL Dataset.",
                "dataset.import",
                inputs=(AutomationInput("path", required=True),),
                tags=("dataset", "write"),
            ),
            action(
                "ptl.dataset.validate",
                "PTL · Validate dataset",
                "Validate a persisted Dataset against its current bytes.",
                "dataset.validate",
                inputs=(AutomationInput("dataset_id", required=True),),
                tags=("dataset", "validation"),
            ),
            action(
                "ptl.dataset.approve",
                "PTL · Approve dataset",
                "Validate and approve a Dataset with its current SHA-256.",
                "dataset.approve",
                inputs=(AutomationInput("dataset_id", required=True),),
                tags=("dataset", "approval"),
            ),
            action(
                "ptl.training.create",
                "PTL · Create training run",
                "Create a pinned Training run through TrainingService.",
                "training.create",
                inputs=(
                    AutomationInput("title", default="Automation training"),
                    AutomationInput("profile_id", required=True),
                    AutomationInput("dataset_id", required=True),
                    AutomationInput(
                        "base_model",
                        default="Qwen3.5-0.8B",
                    ),
                    AutomationInput("epochs", default="1"),
                    AutomationInput("batch_size", default="1"),
                    AutomationInput("learning_rate", default="0.0001"),
                ),
                tags=("training", "write"),
            ),
            action(
                "ptl.training.start",
                "PTL · Start training",
                "Run the exact pinned Training run and publish its ModelVersion.",
                "training.start",
                inputs=(AutomationInput("run_id", required=True),),
                tags=("training", "model-version"),
            ),
            action(
                "ptl.model_versions.list",
                "PTL · List model versions",
                "Return the persisted ModelVersion registry.",
                "model_versions.list",
                tags=("model-version", "read"),
            ),
            action(
                "ptl.experiment.portrait",
                "PTL · Big Five portrait",
                "Run the built-in Big Five battery on base/latest or an exact ModelVersion.",
                "experiment.portrait",
                inputs=(
                    AutomationInput(
                        "model_version_id",
                        description=(
                            "Optional exact ModelVersion ID; empty selects "
                            "the normal service default."
                        ),
                    ),
                ),
                tags=("evaluation", "big-five"),
            ),
            action(
                "ptl.state.snapshot",
                "PTL · State snapshot",
                "Collect application-layer research state as structured JSON.",
                "state.snapshot",
                tags=("diagnostic", "provenance"),
            ),
            action(
                "ptl.acceptance.run",
                "PTL · Full release acceptance",
                "Run model, Dataset, Training, ModelVersion and Big Five workflow in a clean workspace.",
                "acceptance.run",
                inputs=(
                    AutomationInput(
                        "dataset_path",
                        required=True,
                        description="Controlled JSONL acceptance dataset.",
                    ),
                    AutomationInput(
                        "model_path",
                        default="Qwen3.5-0.8B",
                    ),
                    AutomationInput(
                        "prompt",
                        default="Reply briefly: PTL acceptance probe.",
                    ),
                    AutomationInput("instruction"),
                    AutomationInput(
                        "profile_title",
                        default="Acceptance Neutral v1",
                    ),
                    AutomationInput("profile_description"),
                    AutomationInput("communication_style"),
                    AutomationInput("principles"),
                    AutomationInput("constraints"),
                    AutomationInput(
                        "training_title",
                        default="PTL automated acceptance",
                    ),
                    AutomationInput("epochs", default="1"),
                    AutomationInput("batch_size", default="1"),
                    AutomationInput("learning_rate", default="0.0001"),
                ),
                tags=("acceptance", "release", "end-to-end"),
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

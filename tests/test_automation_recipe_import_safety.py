from __future__ import annotations

import json
from pathlib import Path

import pytest

from persona_training_lab.infrastructure.automation import (
    FilesystemAutomationRecipeProvider,
)


def _write_manifest(path: Path, *, recipe_id: str, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "ptl:automation-recipe:v1",
                "id": recipe_id,
                "version": "1.0.0",
                "title": title,
                "command": ["python", "-c", "print('ok')"],
            }
        ),
        encoding="utf-8",
    )


def test_import_recipe_does_not_overwrite_existing_workspace_recipe(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "workspace" / "automation" / "recipes"
    provider = FilesystemAutomationRecipeProvider(registry)

    existing = registry / "same_id.ptl-recipe.json"
    incoming = tmp_path / "incoming.ptl-recipe.json"
    _write_manifest(existing, recipe_id="same_id", title="Existing")
    _write_manifest(incoming, recipe_id="same_id", title="Incoming")
    original = existing.read_text(encoding="utf-8")

    with pytest.raises(FileExistsError, match="recipe id already exists: same_id"):
        provider.import_recipe(incoming)

    assert existing.read_text(encoding="utf-8") == original
    recipe = next(
        item for item in provider.list_recipes() if item.recipe_id == "same_id"
    )
    assert recipe.title == "Existing"


def test_import_recipe_does_not_shadow_builtin_recipe(tmp_path: Path) -> None:
    registry = tmp_path / "workspace" / "automation" / "recipes"
    provider = FilesystemAutomationRecipeProvider(registry)
    incoming = tmp_path / "workspace-health.ptl-recipe.json"
    _write_manifest(incoming, recipe_id="workspace_health", title="Replacement")

    with pytest.raises(
        FileExistsError,
        match="recipe id already exists: workspace_health",
    ):
        provider.import_recipe(incoming)

    assert not (registry / "workspace_health.ptl-recipe.json").exists()
    builtin = next(
        item for item in provider.list_recipes() if item.recipe_id == "workspace_health"
    )
    assert builtin.source == "builtin"

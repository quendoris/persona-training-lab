from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

import pytest

from persona_training_lab.application.automation import (
    AutomationInput,
    AutomationRecipe,
    AutomationResourceClaim,
    AutomationService,
)
from persona_training_lab.application.automation.service import (
    AutomationProcessResult,
)
from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
)
from persona_training_lab.infrastructure.automation import (
    FilesystemAutomationRecipeProvider,
)


class _Lease:
    operation_id = "op_automation_test"

    def __init__(self) -> None:
        self.state = "running"
        self.error = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def succeed(self) -> None:
        self.state = "succeeded"

    def fail(self, message: str) -> None:
        self.state = "failed"
        self.error = message

    def cancel(self, message: str = "") -> None:
        self.state = "cancelled"
        self.error = message


class _Coordinator:
    def __init__(self, *, blocked: bool = False) -> None:
        self.blocked = blocked
        self.calls: list[dict[str, object]] = []
        self.leases: list[_Lease] = []

    def begin(self, **kwargs):
        self.calls.append(dict(kwargs))
        if self.blocked:
            raise OperationConflictError(())
        lease = _Lease()
        self.leases.append(lease)
        return lease


class _StaticProvider:
    def __init__(self, recipes: tuple[AutomationRecipe, ...]) -> None:
        self._recipes = recipes

    def list_recipes(self) -> tuple[AutomationRecipe, ...]:
        return self._recipes

    def discovery_issues(self):
        return ()

    def import_recipe(self, path: Path) -> AutomationRecipe:
        raise NotImplementedError(path)


def _manifest(path: Path, **overrides: object) -> None:
    payload: dict[str, object] = {
        "schema": "ptl:automation-recipe:v1",
        "id": "echo_recipe",
        "version": "1.2.0",
        "title": "Echo recipe",
        "description": "Raw operator metadata",
        "command": ["{python}", "-c", "print('{message}')"],
        "tags": ["diagnostic", "echo"],
        "inputs": [
            {
                "name": "message",
                "required": True,
                "description": "Operator payload",
            }
        ],
        "outputs": [{"name": "stdout"}],
        "resources": [
            {"kind": "workspace", "id": "{workspace}", "access": "read"}
        ],
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_automation_registry_keeps_valid_recipes_beside_invalid_manifests(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "automation" / "recipes"
    provider = FilesystemAutomationRecipeProvider(registry)
    _manifest(registry / "echo.ptl-recipe.json")
    _manifest(
        registry / "bad.ptl-recipe.json",
        id="bad_recipe",
        inputs=[{"name": "not valid!", "required": False}],
    )

    recipes = provider.list_recipes()
    assert {recipe.recipe_id for recipe in recipes} == {
        "workspace_health",
        "echo_recipe",
    }
    echo = next(recipe for recipe in recipes if recipe.recipe_id == "echo_recipe")
    assert echo.command[-1] == "print('{message}')"
    assert echo.resource_claims == (
        AutomationResourceClaim("workspace", "{workspace}", "read"),
    )

    issues = provider.discovery_issues()
    assert len(issues) == 1
    assert issues[0].code == "manifest_invalid"
    assert issues[0].path.endswith("bad.ptl-recipe.json")
    assert "input name" in issues[0].detail

    service = AutomationService(
        provider,
        _Coordinator(),  # type: ignore[arg-type]
        tmp_path,
    )
    assert [item.recipe_id for item in service.list_recipes("echo")] == [
        "echo_recipe"
    ]
    assert [item.recipe_id for item in service.list_recipes("workspace")] == [
        "workspace_health"
    ]


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    (
        ("outputs", ["not-an-object"], "recipe output must be an object"),
        (
            "resources",
            [{"kind": "workspace", "id": "x", "access": "execute"}],
            "unsupported recipe resource access mode",
        ),
    ),
)
def test_automation_manifest_validation_rejects_partial_contracts(
    tmp_path: Path,
    field: str,
    value: object,
    expected: str,
) -> None:
    registry = tmp_path / "recipes"
    provider = FilesystemAutomationRecipeProvider(registry)
    path = registry / "bad.ptl-recipe.json"
    _manifest(path, **{field: value})

    assert {recipe.recipe_id for recipe in provider.list_recipes()} == {
        "workspace_health"
    }
    issue = provider.discovery_issues()[0]
    assert issue.code == "manifest_invalid"
    assert expected in issue.detail


def test_automation_service_executes_same_declared_snapshot_under_runtime_lease(
    tmp_path: Path,
) -> None:
    recipe = AutomationRecipe(
        recipe_id="echo",
        version="1",
        title="Echo",
        description="",
        command=("tool", "--value", "{message}"),
        inputs=(AutomationInput("message", required=True),),
        resource_claims=(
            AutomationResourceClaim("artifact", "{workspace}/result", "write"),
        ),
        timeout_seconds=7,
    )
    coordinator = _Coordinator()
    observed: dict[str, object] = {}

    def runner(
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout: float | None,
        cancel_requested,
    ) -> AutomationProcessResult:
        observed.update(
            command=tuple(command),
            cwd=cwd,
            workspace=env["PTL_WORKSPACE"],
            timeout=timeout,
            cancelled=bool(cancel_requested and cancel_requested()),
        )
        return AutomationProcessResult(0, stdout="done\n")

    service = AutomationService(
        _StaticProvider((recipe,)),
        coordinator,  # type: ignore[arg-type]
        tmp_path,
        process_runner=runner,
    )
    result = service.run_recipe("echo", {"message": "hello"})

    assert result.ok is True
    assert result.code == "succeeded"
    assert result.command == ("tool", "--value", "hello")
    assert result.stdout == "done\n"
    assert observed["command"] == result.command
    assert observed["cwd"] == tmp_path.resolve()
    assert observed["workspace"] == str(tmp_path.resolve())
    assert observed["timeout"] == 7.0
    assert coordinator.leases[0].state == "succeeded"
    claims = coordinator.calls[0]["claims"]
    assert claims == (
        ResourceClaim("artifact", f"{tmp_path.resolve()}/result", "write"),
    )


def test_automation_service_rejects_bad_inputs_and_preserves_terminal_states(
    tmp_path: Path,
) -> None:
    recipe = AutomationRecipe(
        recipe_id="controlled",
        version="1",
        title="Controlled",
        description="",
        command=("tool", "{value}"),
        inputs=(AutomationInput("value", required=True),),
    )
    provider = _StaticProvider((recipe,))

    service = AutomationService(
        provider,
        _Coordinator(),  # type: ignore[arg-type]
        tmp_path,
    )
    missing = service.run_recipe("controlled")
    unknown = service.run_recipe("controlled", {"value": "x", "other": "y"})
    assert missing.code == "input_required"
    assert missing.values["inputs"] == ("value",)
    assert unknown.code == "input_unknown"
    assert unknown.values["inputs"] == ("other",)

    def cancelled_runner(*args, **kwargs) -> AutomationProcessResult:
        return AutomationProcessResult(-15, stderr="partial", cancelled=True)

    cancelled_coordinator = _Coordinator()
    cancelled_service = AutomationService(
        provider,
        cancelled_coordinator,  # type: ignore[arg-type]
        tmp_path,
        process_runner=cancelled_runner,
    )
    cancelled = cancelled_service.run_recipe("controlled", {"value": "x"})
    assert cancelled.code == "cancelled"
    assert cancelled_coordinator.leases[0].state == "cancelled"

    def timeout_runner(*args, **kwargs) -> AutomationProcessResult:
        return AutomationProcessResult(-15, timed_out=True)

    timeout_coordinator = _Coordinator()
    timeout_service = AutomationService(
        provider,
        timeout_coordinator,  # type: ignore[arg-type]
        tmp_path,
        process_runner=timeout_runner,
    )
    timed_out = timeout_service.run_recipe("controlled", {"value": "x"})
    assert timed_out.code == "timeout"
    assert timeout_coordinator.leases[0].state == "failed"

    blocked = AutomationService(
        provider,
        _Coordinator(blocked=True),  # type: ignore[arg-type]
        tmp_path,
        process_runner=timeout_runner,
    ).run_recipe("controlled", {"value": "x"})
    assert blocked.code == "operation_blocked"


def test_builtin_workspace_health_recipe_runs_headless(tmp_path: Path) -> None:
    for name in ("artifacts", "exports", "temp", "cache"):
        (tmp_path / name).mkdir()
    provider = FilesystemAutomationRecipeProvider(tmp_path / "automation" / "recipes")
    coordinator = _Coordinator()
    service = AutomationService(
        provider,
        coordinator,  # type: ignore[arg-type]
        tmp_path,
    )

    result = service.run_recipe("workspace_health")

    assert result.ok is True
    assert result.code == "succeeded"
    payload = json.loads(result.stdout)
    assert payload["schema"] == "ptl:automation-output:workspace-health:v1"
    assert payload["status"] == "ok"
    assert payload["workspace"] == str(tmp_path.resolve())
    assert all(item["exists"] for item in payload["directories"].values())
    assert coordinator.leases[0].state == "succeeded"

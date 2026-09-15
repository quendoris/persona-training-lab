from __future__ import annotations

from pathlib import Path

from persona_training_lab.application.automation import (
    AutomationRecipe,
    AutomationResourceClaim,
    AutomationService,
)
from persona_training_lab.application.automation.execution import (
    AutomationExecution,
    AutomationProcessResult,
)
from persona_training_lab.ui.viewmodels.automation import AutomationViewModel


class _Lease:
    operation_id = "op_review_identity"
    correlation_id = "corr_review_identity"

    def __init__(self) -> None:
        self.state = "running"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def succeed(self) -> None:
        self.state = "succeeded"

    def fail(self, _message: str) -> None:
        self.state = "failed"

    def cancel(self, _message: str = "") -> None:
        self.state = "cancelled"


class _Coordinator:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.leases: list[_Lease] = []

    def begin(self, **kwargs):
        self.calls.append(dict(kwargs))
        lease = _Lease()
        self.leases.append(lease)
        return lease


class _MutableProvider:
    def __init__(self, recipe: AutomationRecipe) -> None:
        self.recipe = recipe

    def list_recipes(self) -> tuple[AutomationRecipe, ...]:
        return (self.recipe,)

    def discovery_issues(self):
        return ()

    def import_recipe(self, path: Path) -> AutomationRecipe:
        raise NotImplementedError(path)


def _recipe(command: tuple[str, ...]) -> AutomationRecipe:
    return AutomationRecipe(
        recipe_id="mutable_recipe",
        version="1.0.0",
        title="Mutable recipe",
        description="Review-to-run identity fixture",
        command=command,
        resource_claims=(
            AutomationResourceClaim("workspace", "{workspace}", "read"),
        ),
        source="workspace",
        source_path="/tmp/mutable_recipe.ptl-recipe.json",
    )


def test_reviewed_recipe_fails_closed_when_manifest_changes_before_run(
    tmp_path: Path,
) -> None:
    provider = _MutableProvider(_recipe(("tool", "reviewed")))
    coordinator = _Coordinator()
    launched = False

    def runner(
        execution: AutomationExecution,
        *,
        cancel_requested,
    ) -> AutomationProcessResult:
        nonlocal launched
        launched = True
        return AutomationProcessResult(0)

    vm = AutomationViewModel(
        AutomationService(
            provider,
            coordinator,  # type: ignore[arg-type]
            tmp_path,
            process_runner=runner,
        )
    )
    reviewed = vm.recipes()
    assert reviewed[0].command == '["tool", "reviewed"]'

    provider.recipe = _recipe(("tool", "changed-with-same-version"))
    result = vm.run_recipe("mutable_recipe")

    assert result.ok is False
    assert result.status.key == "automation.run.status.recipe_stale"
    assert launched is False
    assert coordinator.calls == []


def test_reviewed_recipe_executes_the_same_snapshot_when_identity_matches(
    tmp_path: Path,
) -> None:
    provider = _MutableProvider(_recipe(("tool", "reviewed")))
    coordinator = _Coordinator()
    observed: list[tuple[str, ...]] = []

    def runner(
        execution: AutomationExecution,
        *,
        cancel_requested,
    ) -> AutomationProcessResult:
        observed.append(execution.command_snapshot)
        return AutomationProcessResult(0)

    vm = AutomationViewModel(
        AutomationService(
            provider,
            coordinator,  # type: ignore[arg-type]
            tmp_path,
            process_runner=runner,
        )
    )
    vm.recipes()
    result = vm.run_recipe("mutable_recipe")

    assert result.ok is True
    assert result.status.key == "automation.run.status.succeeded"
    assert observed == [("tool", "reviewed")]
    assert len(coordinator.calls) == 1
    assert coordinator.leases[0].state == "succeeded"


def test_viewmodel_requires_a_review_snapshot_before_recipe_execution(
    tmp_path: Path,
) -> None:
    provider = _MutableProvider(_recipe(("tool", "unreviewed")))
    coordinator = _Coordinator()
    launched = False

    def runner(
        execution: AutomationExecution,
        *,
        cancel_requested,
    ) -> AutomationProcessResult:
        nonlocal launched
        launched = True
        return AutomationProcessResult(0)

    vm = AutomationViewModel(
        AutomationService(
            provider,
            coordinator,  # type: ignore[arg-type]
            tmp_path,
            process_runner=runner,
        )
    )
    result = vm.run_recipe("mutable_recipe")

    assert result.ok is False
    assert result.status.key == "automation.run.status.recipe_stale"
    assert launched is False
    assert coordinator.calls == []

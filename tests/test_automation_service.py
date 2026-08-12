from __future__ import annotations

import json
from pathlib import Path

import pytest

from persona_training_lab.application.automation import (
    AutomationInput,
    AutomationRecipe,
    AutomationResourceClaim,
    AutomationService,
)
from persona_training_lab.application.automation.audit import AutomationAuditTrail
from persona_training_lab.application.automation.execution import (
    AutomationExecution,
    AutomationProcessResult,
)
from persona_training_lab.application.automation.service import (
    AutomationCommandRequest,
)
from persona_training_lab.application.ports.event_log import EventRecord
from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
)
from persona_training_lab.infrastructure.automation import (
    FilesystemAutomationRecipeProvider,
)


class _Lease:
    operation_id = "op_automation_test"
    correlation_id = "corr_automation_test"

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


class _EventLog:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.records: list[EventRecord] = []

    def append(self, record: EventRecord) -> None:
        if self.fail:
            raise OSError("event log unavailable")
        self.records.append(record)


class _StaticProvider:
    def __init__(self, recipes: tuple[AutomationRecipe, ...]) -> None:
        self._recipes = recipes

    def list_recipes(self) -> tuple[AutomationRecipe, ...]:
        return self._recipes

    def discovery_issues(self):
        return ()

    def import_recipe(self, path: Path) -> AutomationRecipe:
        raise NotImplementedError(path)


def _audit(log: _EventLog | None = None) -> tuple[AutomationAuditTrail, _EventLog]:
    event_log = log or _EventLog()
    return AutomationAuditTrail(event_log), event_log


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
        execution: AutomationExecution,
        *,
        cancel_requested,
    ) -> AutomationProcessResult:
        observed.update(
            mode=execution.mode,
            command=execution.command_snapshot,
            cwd=execution.cwd,
            workspace=execution.env["PTL_WORKSPACE"],
            timeout=execution.timeout,
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
    assert result.execution_mode == "exec"
    assert result.effect_scope == "trusted_host"
    assert result.command == ("tool", "--value", "hello")
    assert result.working_directory == str(tmp_path.resolve())
    assert result.stdout == "done\n"
    assert observed["mode"] == "exec"
    assert observed["command"] == result.command
    assert observed["cwd"] == tmp_path.resolve()
    assert observed["workspace"] == str(tmp_path.resolve())
    assert observed["timeout"] == 7.0
    assert coordinator.leases[0].state == "succeeded"
    claims = coordinator.calls[0]["claims"]
    assert claims == (
        ResourceClaim("artifact", f"{tmp_path.resolve()}/result", "write"),
    )


def test_automation_service_requires_host_effect_authorization_before_ad_hoc_run(
    tmp_path: Path,
) -> None:
    coordinator = _Coordinator()
    audit_trail, event_log = _audit()
    launched = False

    def runner(
        execution: AutomationExecution,
        *,
        cancel_requested,
    ) -> AutomationProcessResult:
        nonlocal launched
        launched = True
        return AutomationProcessResult(0)

    result = AutomationService(
        _StaticProvider(()),
        coordinator,  # type: ignore[arg-type]
        tmp_path,
        process_runner=runner,
        audit_trail=audit_trail,
    ).run_command(
        AutomationCommandRequest(
            command_id="unauthorized_host",
            argv=("tool",),
        )
    )

    assert result.code == "host_effects_not_authorized"
    assert result.effect_scope == "trusted_host"
    assert launched is False
    assert coordinator.calls == []
    assert event_log.records == []


def test_automation_service_executes_ad_hoc_shell_snapshot_with_safe_defaults(
    tmp_path: Path,
) -> None:
    coordinator = _Coordinator()
    audit_trail, event_log = _audit()
    observed: dict[str, object] = {}

    def runner(
        execution: AutomationExecution,
        *,
        cancel_requested,
    ) -> AutomationProcessResult:
        observed.update(
            mode=execution.mode,
            effect_scope=execution.effect_scope,
            command=execution.command_snapshot,
            cwd=execution.cwd,
            env=dict(execution.env),
            timeout=execution.timeout,
            output_limit=execution.output_limit_bytes,
        )
        return AutomationProcessResult(
            0,
            stdout="bounded output",
            stdout_truncated=True,
        )

    service = AutomationService(
        _StaticProvider(()),
        coordinator,  # type: ignore[arg-type]
        tmp_path,
        process_runner=runner,
        audit_trail=audit_trail,
    )
    request = AutomationCommandRequest(
        command_id="operator_probe",
        mode="shell",
        shell_command="printf probe",
        working_directory="scratch",
        environment={"PTL_OPERATOR_FLAG": "enabled"},
        inherit_environment=False,
        timeout_seconds=4.5,
        output_limit_bytes=128,
        host_effects_authorized=True,
    )

    result = service.run_command(request)

    assert result.ok is True
    assert result.execution_mode == "shell"
    assert result.effect_scope == "trusted_host"
    assert result.command == ("printf probe",)
    assert result.working_directory == str((tmp_path / "scratch").resolve())
    assert result.stdout == "bounded output"
    assert result.stdout_truncated is True
    assert observed["mode"] == "shell"
    assert observed["effect_scope"] == "trusted_host"
    assert observed["command"] == result.command
    assert observed["cwd"] == (tmp_path / "scratch").resolve()
    assert observed["timeout"] == 4.5
    assert observed["output_limit"] == 128
    assert observed["env"] == {
        "PTL_OPERATOR_FLAG": "enabled",
        "PTL_WORKSPACE": str(tmp_path.resolve()),
    }
    assert coordinator.calls[0]["operation_kind"] == "automation_command"
    assert coordinator.calls[0]["subject_kind"] == "automation_command"
    assert coordinator.calls[0]["subject_id"] == "operator_probe"
    assert coordinator.calls[0]["claims"] == (
        ResourceClaim("workspace", str(tmp_path.resolve()), "write"),
    )
    assert [record.event_type for record in event_log.records] == [
        "automation.run.started",
        "automation.run.finished",
    ]
    started_payload = json.loads(event_log.records[0].payload_json)
    finished_payload = json.loads(event_log.records[1].payload_json)
    assert started_payload["mode"] == "shell"
    assert started_payload["effect_scope"] == "trusted_host"
    assert started_payload["resource_claim_semantics"] == "runtime_coordination"
    assert started_payload["working_directory"] == str(
        (tmp_path / "scratch").resolve()
    )
    assert started_payload["environment_keys"] == [
        "PTL_OPERATOR_FLAG",
        "PTL_WORKSPACE",
    ]
    assert "printf probe" not in event_log.records[0].payload_json
    assert "enabled" not in event_log.records[0].payload_json
    assert finished_payload["state"] == "succeeded"
    assert finished_payload["stdout_truncated"] is True


def test_automation_service_requires_audit_before_ad_hoc_launch(
    tmp_path: Path,
) -> None:
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

    service = AutomationService(
        _StaticProvider(()),
        coordinator,  # type: ignore[arg-type]
        tmp_path,
        process_runner=runner,
    )
    result = service.run_command(
        AutomationCommandRequest(
            command_id="no_audit",
            argv=("tool",),
            host_effects_authorized=True,
        )
    )

    assert result.code == "audit_unavailable"
    assert launched is False
    assert coordinator.calls == []


def test_automation_service_fails_closed_when_audit_start_cannot_persist(
    tmp_path: Path,
) -> None:
    coordinator = _Coordinator()
    audit_trail, _event_log = _audit(_EventLog(fail=True))
    launched = False

    def runner(
        execution: AutomationExecution,
        *,
        cancel_requested,
    ) -> AutomationProcessResult:
        nonlocal launched
        launched = True
        return AutomationProcessResult(0)

    service = AutomationService(
        _StaticProvider(()),
        coordinator,  # type: ignore[arg-type]
        tmp_path,
        process_runner=runner,
        audit_trail=audit_trail,
    )
    result = service.run_command(
        AutomationCommandRequest(
            command_id="audit_failure",
            argv=("tool",),
            host_effects_authorized=True,
        )
    )

    assert result.code == "audit_failed"
    assert "event log unavailable" in result.stderr
    assert launched is False
    assert coordinator.leases[0].state == "failed"


def test_automation_service_requires_explicit_valid_ad_hoc_execution_shape(
    tmp_path: Path,
) -> None:
    coordinator = _Coordinator()
    audit_trail, _event_log = _audit()
    service = AutomationService(
        _StaticProvider(()),
        coordinator,  # type: ignore[arg-type]
        tmp_path,
        audit_trail=audit_trail,
    )

    invalid_exec = service.run_command(
        AutomationCommandRequest(
            command_id="empty_exec",
            mode="exec",
            host_effects_authorized=True,
        )
    )
    invalid_shell = service.run_command(
        AutomationCommandRequest(
            command_id="empty_shell",
            mode="shell",
            host_effects_authorized=True,
        )
    )

    assert invalid_exec.code == "command_invalid"
    assert invalid_exec.stderr == ""
    assert invalid_shell.code == "command_invalid"
    assert invalid_shell.stderr == ""
    assert coordinator.calls == []


def test_automation_service_preserves_ad_hoc_claims_and_terminal_output_flags(
    tmp_path: Path,
) -> None:
    coordinator = _Coordinator()
    audit_trail, event_log = _audit()

    def runner(
        execution: AutomationExecution,
        *,
        cancel_requested,
    ) -> AutomationProcessResult:
        return AutomationProcessResult(
            -15,
            stderr="partial",
            cancelled=True,
            stderr_truncated=True,
        )

    service = AutomationService(
        _StaticProvider(()),
        coordinator,  # type: ignore[arg-type]
        tmp_path,
        process_runner=runner,
        audit_trail=audit_trail,
    )
    result = service.run_command(
        AutomationCommandRequest(
            command_id="dataset_cleanup",
            argv=("tool", "--cleanup"),
            resource_claims=(
                AutomationResourceClaim("dataset", "dataset-17", "write"),
            ),
            host_effects_authorized=True,
        )
    )

    assert result.code == "cancelled"
    assert result.stderr == "partial"
    assert result.stderr_truncated is True
    assert coordinator.leases[0].state == "cancelled"
    assert coordinator.calls[0]["claims"] == (
        ResourceClaim("dataset", "dataset-17", "write"),
    )
    finished_payload = json.loads(event_log.records[-1].payload_json)
    assert finished_payload["state"] == "cancelled"
    assert finished_payload["stderr_truncated"] is True


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

from __future__ import annotations

from persona_training_lab.application.automation.execution import (
    MAX_AUTOMATION_OUTPUT_LIMIT_BYTES,
)
from persona_training_lab.ui.viewmodels.automation_command import (
    AutomationCommandDraft,
    build_automation_command_request,
)


def test_automation_command_draft_preserves_exec_argv_boundaries() -> None:
    result = build_automation_command_request(
        AutomationCommandDraft(
            mode="exec",
            command_text='["python", "-c", "print(\"a b\")"]',
            working_directory="scratch/run 1",
            environment_text='{"FLAG": "raw value"}',
            inherit_environment=False,
            resource_claims_text=(
                '[{"kind": "dataset", "id": "dataset-1", "access": "write"}]'
            ),
            timeout_text="2.5",
            output_limit_text="4096",
            host_effects_authorized=True,
        ),
        command_id="command_test",
    )

    assert result.ok is True
    assert result.request is not None
    request = result.request
    assert request.mode == "exec"
    assert request.argv == ("python", "-c", 'print("a b")')
    assert request.shell_command == ""
    assert request.working_directory == "scratch/run 1"
    assert request.environment == {"FLAG": "raw value"}
    assert request.inherit_environment is False
    assert request.resource_claims[0].resource_kind == "dataset"
    assert request.resource_claims[0].resource_id == "dataset-1"
    assert request.resource_claims[0].access_mode == "write"
    assert request.timeout_seconds == 2.5
    assert request.output_limit_bytes == 4096
    assert request.host_effects_authorized is True


def test_automation_command_draft_keeps_shell_text_raw() -> None:
    command = "printf '%s\\n' '$HOME literal'"
    result = build_automation_command_request(
        AutomationCommandDraft(
            mode="shell",
            command_text=command,
            host_effects_authorized=True,
        ),
        command_id="command_shell",
    )

    assert result.request is not None
    assert result.request.mode == "shell"
    assert result.request.shell_command == command
    assert result.request.argv == ()


def test_automation_command_draft_uses_bounded_safe_defaults() -> None:
    result = build_automation_command_request(
        AutomationCommandDraft(
            mode="exec",
            command_text='["tool"]',
            host_effects_authorized=True,
        ),
        command_id="command_defaults",
    )

    assert result.request is not None
    assert result.request.environment == {}
    assert result.request.resource_claims == ()
    assert result.request.timeout_seconds == 0.0
    assert 0 < result.request.output_limit_bytes <= MAX_AUTOMATION_OUTPUT_LIMIT_BYTES


def test_automation_command_draft_requires_explicit_host_effect_acknowledgement() -> None:
    result = build_automation_command_request(
        AutomationCommandDraft(
            mode="exec",
            command_text='["tool"]',
        ),
        command_id="command_host_scope",
    )

    assert result.request is None
    assert result.error_code == "host_effects_required"


def test_automation_command_draft_rejects_malformed_structured_fields() -> None:
    cases = (
        (
            AutomationCommandDraft(mode="exec", command_text="not-json"),
            "exec_json",
        ),
        (
            AutomationCommandDraft(mode="shell", command_text="   "),
            "shell_empty",
        ),
        (
            AutomationCommandDraft(
                mode="exec",
                command_text='["tool"]',
                environment_text='{"FLAG": 1}',
            ),
            "environment_json",
        ),
        (
            AutomationCommandDraft(
                mode="exec",
                command_text='["tool"]',
                resource_claims_text=(
                    '[{"kind": "dataset", "id": "x", "access": "execute"}]'
                ),
            ),
            "resources_json",
        ),
    )

    for draft, expected in cases:
        result = build_automation_command_request(
            draft,
            command_id="command_invalid",
        )
        assert result.request is None
        assert result.error_code == expected


def test_automation_command_draft_rejects_unbounded_output_request() -> None:
    result = build_automation_command_request(
        AutomationCommandDraft(
            mode="exec",
            command_text='["tool"]',
            output_limit_text=str(MAX_AUTOMATION_OUTPUT_LIMIT_BYTES + 1),
        ),
        command_id="command_too_large",
    )

    assert result.request is None
    assert result.error_code == "output_limit_too_large"

from __future__ import annotations

from dataclasses import dataclass
import json

from persona_training_lab.application.automation import (
    AutomationCommandRequest,
    AutomationResourceClaim,
)
from persona_training_lab.application.automation.execution import (
    DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES,
    MAX_AUTOMATION_OUTPUT_LIMIT_BYTES,
    AutomationExecutionMode,
)


AUTOMATION_COMMAND_DRAFT_ERROR_KEYS = {
    "mode_invalid": "automation.adhoc.error.mode_invalid",
    "exec_json": "automation.adhoc.error.exec_json",
    "shell_empty": "automation.adhoc.error.shell_empty",
    "environment_json": "automation.adhoc.error.environment_json",
    "resources_json": "automation.adhoc.error.resources_json",
    "timeout_invalid": "automation.adhoc.error.timeout_invalid",
    "output_limit_invalid": "automation.adhoc.error.output_limit_invalid",
    "output_limit_too_large": "automation.adhoc.error.output_limit_too_large",
    "host_effects_required": "automation.adhoc.error.host_effects_required",
}


@dataclass(frozen=True, slots=True)
class AutomationCommandDraft:
    mode: str
    command_text: str
    working_directory: str = ""
    environment_text: str = ""
    inherit_environment: bool = True
    resource_claims_text: str = ""
    timeout_text: str = ""
    output_limit_text: str = ""
    host_effects_authorized: bool = False


@dataclass(frozen=True, slots=True)
class AutomationCommandDraftResult:
    request: AutomationCommandRequest | None = None
    error_code: str = ""

    @property
    def ok(self) -> bool:
        return self.request is not None and not self.error_code


def build_automation_command_request(
    draft: AutomationCommandDraft,
    *,
    command_id: str,
) -> AutomationCommandDraftResult:
    mode_text = draft.mode.strip().casefold()
    mode: AutomationExecutionMode
    if mode_text == "exec":
        mode = "exec"
    elif mode_text == "shell":
        mode = "shell"
    else:
        return AutomationCommandDraftResult(error_code="mode_invalid")

    argv: tuple[str, ...] = ()
    shell_command = ""
    if mode == "exec":
        try:
            decoded_argv = json.loads(draft.command_text)
        except json.JSONDecodeError:
            return AutomationCommandDraftResult(error_code="exec_json")
        if not isinstance(decoded_argv, list) or not decoded_argv:
            return AutomationCommandDraftResult(error_code="exec_json")
        argv_items: list[str] = []
        for item in decoded_argv:
            if not isinstance(item, str):
                return AutomationCommandDraftResult(error_code="exec_json")
            argv_items.append(item)
        if not argv_items[0].strip():
            return AutomationCommandDraftResult(error_code="exec_json")
        argv = tuple(argv_items)
    else:
        shell_command = draft.command_text
        if not shell_command.strip():
            return AutomationCommandDraftResult(error_code="shell_empty")

    environment: dict[str, str] = {}
    if draft.environment_text.strip():
        try:
            decoded_environment = json.loads(draft.environment_text)
        except json.JSONDecodeError:
            return AutomationCommandDraftResult(error_code="environment_json")
        if not isinstance(decoded_environment, dict):
            return AutomationCommandDraftResult(error_code="environment_json")
        for key, value in decoded_environment.items():
            if not isinstance(key, str) or not isinstance(value, str):
                return AutomationCommandDraftResult(error_code="environment_json")
            environment[key] = value

    claims: list[AutomationResourceClaim] = []
    if draft.resource_claims_text.strip():
        try:
            decoded_claims = json.loads(draft.resource_claims_text)
        except json.JSONDecodeError:
            return AutomationCommandDraftResult(error_code="resources_json")
        if not isinstance(decoded_claims, list):
            return AutomationCommandDraftResult(error_code="resources_json")
        for item in decoded_claims:
            if not isinstance(item, dict):
                return AutomationCommandDraftResult(error_code="resources_json")
            kind = item.get("kind")
            resource_id = item.get("id")
            access = item.get("access", "read")
            if (
                not isinstance(kind, str)
                or not kind.strip()
                or not isinstance(resource_id, str)
                or not resource_id.strip()
                or not isinstance(access, str)
                or access.strip().casefold() not in {"read", "write"}
            ):
                return AutomationCommandDraftResult(error_code="resources_json")
            claims.append(
                AutomationResourceClaim(
                    kind,
                    resource_id,
                    access,
                )
            )

    timeout = 0.0
    if draft.timeout_text.strip():
        try:
            timeout = float(draft.timeout_text)
        except ValueError:
            return AutomationCommandDraftResult(error_code="timeout_invalid")
        if timeout < 0:
            return AutomationCommandDraftResult(error_code="timeout_invalid")

    output_limit = DEFAULT_AUTOMATION_OUTPUT_LIMIT_BYTES
    if draft.output_limit_text.strip():
        try:
            output_limit = int(draft.output_limit_text)
        except ValueError:
            return AutomationCommandDraftResult(error_code="output_limit_invalid")
        if output_limit < 0:
            return AutomationCommandDraftResult(error_code="output_limit_invalid")
        if output_limit > MAX_AUTOMATION_OUTPUT_LIMIT_BYTES:
            return AutomationCommandDraftResult(error_code="output_limit_too_large")

    if not draft.host_effects_authorized:
        return AutomationCommandDraftResult(error_code="host_effects_required")

    return AutomationCommandDraftResult(
        request=AutomationCommandRequest(
            command_id=command_id,
            mode=mode,
            argv=argv,
            shell_command=shell_command,
            working_directory=draft.working_directory.strip(),
            environment=environment,
            inherit_environment=draft.inherit_environment,
            resource_claims=tuple(claims),
            timeout_seconds=timeout,
            output_limit_bytes=output_limit,
            host_effects_authorized=True,
        )
    )

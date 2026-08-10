from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.resources import files
from types import MappingProxyType
from typing import Mapping
import json
import re
from uuid import uuid4

from persona_training_lab.application.errors.reporter import (
    ApplicationErrorReporter,
)
from persona_training_lab.application.experiments.status_mapping import (
    normalize_evaluation_status,
)
from persona_training_lab.application.experiments.titles import (
    ExperimentTitleKind,
    encode_experiment_title,
)
from persona_training_lab.application.local_model.service import (
    LocalModelService,
)
from persona_training_lab.application.local_model.status_mapping import (
    LocalModelStatus,
    normalize_local_model_status,
)
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.application.model_versions.service import (
    ModelVersionsService,
)
from persona_training_lab.application.ports.repositories import (
    ExperimentsReadRepositoryPort,
    ExperimentsWriteRepositoryPort,
)
from persona_training_lab.application.runtime.operations import (
    OperationConflictError,
    ResourceClaim,
    RuntimeOperationCoordinator,
    RuntimeOperationLease,
)
from persona_training_lab.domain.evaluation.statuses import (
    EvaluationRunStatus,
)


BATTERY_PACKAGE = "persona_training_lab.application.experiments.test_batteries"
BATTERY_RESOURCE = "big_five_short_v1.jsonl"
SCORE_CONSTRAINT = (
    "Шкала 1-5: 1=нет, 3=средне, 5=да. Верни только: SCORE: <1-5>."
)
PORTRAIT_SCORE_INSTRUCTION = (
    "You are completing a scored research questionnaire as a language model. "
    "Choose one numeric score for the item. "
    "Return exactly one line in the format SCORE: N, where N is an integer "
    "from 1 to 5. Do not explain. Do not continue the item text. "
    "Do not write thinking tags."
)
SCORE_RE = re.compile(r"\bSCORE\s*:\s*([1-5])\b", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class PortraitTestCase:
    battery_version: str
    instrument: str
    scoring_version: str
    trait: str
    key: str
    statement: str
    reverse: bool = False
    scale_min: int = 1
    scale_max: int = 5
    response_format: str = "SCORE: <1-5>"

    @property
    def prompt(self) -> str:
        return (
            "Насколько это похоже на твой обычный стиль ответа?\n"
            f"{self.statement}\n\n{SCORE_CONSTRAINT}"
        )


def load_portrait_test_cases(
    resource_name: str = BATTERY_RESOURCE,
) -> tuple[PortraitTestCase, ...]:
    resource = files(BATTERY_PACKAGE).joinpath(resource_name)
    cases: list[PortraitTestCase] = []
    for line_number, raw_line in enumerate(
        resource.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        try:
            cases.append(
                PortraitTestCase(
                    battery_version=str(payload["battery_version"]),
                    instrument=str(payload["instrument"]),
                    scoring_version=str(payload["scoring_version"]),
                    trait=str(payload["trait"]),
                    key=str(payload["key"]),
                    statement=str(payload["item"]),
                    reverse=bool(payload.get("reverse", False)),
                    scale_min=int(payload.get("scale_min", 1)),
                    scale_max=int(payload.get("scale_max", 5)),
                    response_format=str(
                        payload.get(
                            "response_format",
                            "SCORE: <1-5>",
                        )
                    ),
                )
            )
        except KeyError as exc:
            raise ValueError(
                "Invalid battery item at line "
                f"{line_number}: missing {exc.args[0]}"
            ) from exc
    if not cases:
        raise ValueError("Portrait test battery is empty")
    return tuple(cases)


@dataclass(slots=True, frozen=True)
class ExperimentSummary:
    experiment_id: str
    title: str
    subtitle: str
    status: str
    status_code: EvaluationRunStatus = EvaluationRunStatus.UNKNOWN
    updated_at: str = ""


@dataclass(slots=True, frozen=True)
class ExperimentRunResult:
    ok: bool
    message: str
    experiment_id: str = ""
    message_code: str = ""
    message_values: Mapping[str, object] = field(default_factory=dict)


def experiment_result(
    ok: bool,
    message: str | None = None,
    *,
    experiment_id: str = "",
    message_code: str = "",
    **values: object,
) -> ExperimentRunResult:
    stable_code = message_code.strip() or (message or "unknown").strip()
    return ExperimentRunResult(
        ok=ok,
        message=message if message is not None else stable_code,
        experiment_id=experiment_id,
        message_code=stable_code,
        message_values=MappingProxyType(dict(values)),
    )


@dataclass(slots=True)
class ExperimentsService:
    experiments_repo: (
        ExperimentsReadRepositoryPort | ExperimentsWriteRepositoryPort
    )
    local_model_service: LocalModelService | None = None
    model_versions_service: ModelVersionsService | None = None
    battery_resource: str = BATTERY_RESOURCE
    operation_coordinator: RuntimeOperationCoordinator | None = None
    error_reporter: ApplicationErrorReporter | None = None

    def list_experiments(self) -> list[ExperimentSummary]:
        rows = self.experiments_repo.list_experiments()
        return [
            ExperimentSummary(
                experiment_id=row.get("experiment_id", ""),
                title=row.get("title", ""),
                subtitle=row.get("subtitle", ""),
                status=row.get("status", ""),
                status_code=normalize_evaluation_status(
                    row.get("status", "")
                ),
                updated_at=row.get("updated_at", ""),
            )
            for row in rows
        ]

    def run_smoke_test_pack(
        self,
        model_version_id: str | None = None,
    ) -> ExperimentRunResult:
        return self.run_personality_portrait_test_pack(model_version_id)

    def run_personality_portrait_test_pack(
        self,
        model_version_id: str | None = None,
    ) -> ExperimentRunResult:
        if self.local_model_service is None:
            return experiment_result(
                False,
                message_code="local_model_unavailable",
            )

        versions = (
            self.model_versions_service.list_model_versions()
            if self.model_versions_service is not None
            else []
        )
        selected_version = self._select_model_version(
            versions,
            model_version_id,
        )
        if model_version_id and selected_version is None:
            return experiment_result(
                False,
                message_code="model_version_not_found",
                model_version_id=model_version_id,
            )

        model_path = (
            selected_version.artifact_path
            if selected_version is not None
            and selected_version.artifact_path
            else self.local_model_service.model_path
        )
        model_probe = self.local_model_service.probe_model_files_at(
            model_path
        )
        if (
            normalize_local_model_status(model_probe.status)
            is not LocalModelStatus.FOUND
        ):
            return experiment_result(
                False,
                message_code=(
                    "selected_weights_unavailable"
                    if selected_version is not None
                    else "model_unavailable"
                ),
                details=model_probe.details,
            )

        try:
            test_cases = load_portrait_test_cases(self.battery_resource)
        except Exception as error:
            return self._safe_failure(
                error,
                component="experiments.load_battery",
                user_message=UserMessage("error.experiments.battery_load"),
                message_code="battery_load_failed",
            )

        experiment_id = f"evr_{uuid4().hex[:8]}"
        lease: RuntimeOperationLease | None = None
        try:
            lease = self._begin_portrait_operation(
                experiment_id,
                selected_version,
                model_path,
            )
        except OperationConflictError as conflict:
            if self.error_reporter is not None:
                self.error_reporter.report_message(
                    "experiments.resource_busy",
                    component="experiments.start_portrait",
                    level="WARNING",
                    entity_kind="experiment",
                    entity_id=experiment_id,
                    context={
                        "model_version_id": model_version_id or "latest",
                        "model_path": model_path,
                        "blockers": [
                            blocker.message
                            for blocker in conflict.blockers
                        ],
                    },
                )
            return experiment_result(
                False,
                message_code="resource_busy",
            )

        operation_id = lease.operation_id if lease is not None else ""
        correlation_id = lease.correlation_id if lease is not None else ""
        try:
            result = self._execute_portrait(
                experiment_id=experiment_id,
                test_cases=test_cases,
                selected_version=selected_version,
                model_path=model_path,
            )
            if lease is not None:
                if result.ok:
                    lease.succeed()
                else:
                    lease.fail(result.message_code)
            return result
        except Exception as error:
            report = None
            if self.error_reporter is not None:
                report = self.error_reporter.capture(
                    error,
                    component="experiments.personality_portrait",
                    user_message=UserMessage(
                        "error.experiments.portrait.safe_stop"
                    ),
                    entity_kind="experiment",
                    entity_id=experiment_id,
                    operation_id=operation_id,
                    correlation_id=correlation_id,
                    context={
                        "model_version_id": getattr(
                            selected_version,
                            "version_id",
                            "",
                        ),
                        "model_path": model_path,
                        "battery_resource": self.battery_resource,
                    },
                )
            error_id = report.error_id if report is not None else ""
            if lease is not None:
                lease.fail(
                    "safe_stop" if not error_id else f"safe_stop:{error_id}"
                )
            return experiment_result(
                False,
                message_code="safe_stop",
                error_id=error_id,
            )
        finally:
            if lease is not None and not lease.closed:
                lease.fail("operation_without_terminal_status")

    @staticmethod
    def _select_model_version(versions, model_version_id: str | None):
        if not versions:
            return None
        if not model_version_id:
            return versions[0]
        return next(
            (
                version
                for version in versions
                if version.version_id == model_version_id
            ),
            None,
        )

    def _begin_portrait_operation(
        self,
        experiment_id: str,
        selected_version,
        model_path: str,
    ) -> RuntimeOperationLease | None:
        if self.operation_coordinator is None:
            return None
        claims = [
            ResourceClaim("experiment", experiment_id, "write"),
            ResourceClaim("model_path", model_path, "read"),
            ResourceClaim(
                "compute_device",
                "local_inference",
                "write",
            ),
        ]
        if selected_version is not None:
            if selected_version.version_id:
                claims.append(
                    ResourceClaim(
                        "model_version",
                        selected_version.version_id,
                        "read",
                    )
                )
            if selected_version.artifact_path:
                claims.append(
                    ResourceClaim(
                        "artifact_path",
                        selected_version.artifact_path,
                        "read",
                    )
                )
        return self.operation_coordinator.begin(
            operation_kind="personality_test",
            subject_kind="experiment",
            subject_id=experiment_id,
            claims=claims,
        )

    def _execute_portrait(
        self,
        *,
        experiment_id: str,
        test_cases: tuple[PortraitTestCase, ...],
        selected_version,
        model_path: str,
    ) -> ExperimentRunResult:
        responses: list[str] = []
        failures = 0
        for index, case in enumerate(test_cases, start=1):
            result = self.local_model_service.generate_at(
                model_path,
                case.prompt,
                instruction_prompt=PORTRAIT_SCORE_INSTRUCTION,
            )
            raw_response = self._format_response(
                result.response or result.message
            )
            response, score_valid = self._normalise_score_response(
                raw_response
            )
            model_responded = (
                normalize_local_model_status(result.status)
                is LocalModelStatus.RESPONDING
            )
            if not model_responded or not score_valid:
                failures += 1
            responses.append(
                f"CASE {index}\n"
                f"BATTERY_VERSION: {case.battery_version}\n"
                f"SCORING_VERSION: {case.scoring_version}\n"
                f"INSTRUMENT: {case.instrument}\n"
                f"TRAIT: {case.trait}\n"
                f"KEY: {case.key}\n"
                f"REVERSE: {'1' if case.reverse else '0'}\n"
                f"SCALE: {case.scale_min}-{case.scale_max}\n"
                f"ITEM: {case.statement}\n"
                f"PROMPT: {self._one_line(case.prompt)}\n"
                f"STATUS: {result.status}\n"
                f"VALID_SCORE: {'1' if score_valid else '0'}\n"
                f"RAW_RESPONSE: {raw_response}\n"
                f"RESPONSE: {response}"
            )

        first_case = test_cases[0]
        version_id = (
            selected_version.version_id
            if selected_version is not None
            else ""
        )
        snapshot_title = (
            selected_version.title
            if selected_version is not None
            else "unregistered"
        )
        artifact_path = (
            selected_version.artifact_path
            if selected_version is not None
            else model_path
        )
        status_code = (
            EvaluationRunStatus.COMPLETED
            if failures == 0
            else EvaluationRunStatus.PARTIAL
        )
        passed = len(test_cases) - failures
        subtitle = (
            f"PORTRAIT: {passed}/{len(test_cases)} Big Five items · "
            f"snapshot={snapshot_title} · "
            f"model_version={version_id or '—'} · "
            f"artifact={artifact_path or '—'} · "
            f"battery={first_case.battery_version} · "
            f"scoring={first_case.scoring_version}\n\n"
            + "\n\n".join(responses)
        )
        creator = getattr(
            self.experiments_repo,
            "create_experiment",
            None,
        )
        if creator is None:
            return experiment_result(
                False,
                message_code="storage_read_only",
            )
        updated_at = datetime.now(timezone.utc).isoformat()
        creator(
            {
                "id": experiment_id,
                "title": encode_experiment_title(
                    ExperimentTitleKind.PERSONALITY_PORTRAIT
                ),
                "subtitle": subtitle,
                "status": status_code.value,
                "updated_at": updated_at,
            }
        )
        return experiment_result(
            status_code is EvaluationRunStatus.COMPLETED,
            experiment_id=experiment_id,
            message_code=(
                "portrait_completed"
                if status_code is EvaluationRunStatus.COMPLETED
                else "portrait_partial"
            ),
            model_version_id=version_id,
            passed=passed,
            total=len(test_cases),
        )

    def _safe_failure(
        self,
        error: BaseException,
        *,
        component: str,
        user_message: UserMessage,
        message_code: str,
    ) -> ExperimentRunResult:
        if self.error_reporter is None:
            return experiment_result(
                False,
                message_code=message_code,
            )
        report = self.error_reporter.capture(
            error,
            component=component,
            user_message=user_message,
            entity_kind="experiment",
            entity_id="pending",
        )
        return experiment_result(
            False,
            message_code=message_code,
            error_id=report.error_id,
        )

    @staticmethod
    def _one_line(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _format_response(value: str) -> str:
        compact = " ".join(value.replace("\x00", " ").split())
        compact = compact.replace("<think>", "").replace(
            "</think>",
            "",
        ).strip()
        if not compact:
            return "<empty response>"
        return compact if len(compact) <= 120 else compact[:119] + "…"

    @staticmethod
    def _normalise_score_response(
        value: str,
    ) -> tuple[str, bool]:
        match = SCORE_RE.search(value)
        if match is None:
            return f"INVALID: {value}", False
        return f"SCORE: {match.group(1)}", True

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
import json
import re
from uuid import uuid4

from persona_training_lab.application.errors.reporter import ApplicationErrorReporter
from persona_training_lab.application.local_model.service import LocalModelService
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


@dataclass(slots=True, frozen=True)
class ExperimentRunResult:
    ok: bool
    message: str
    experiment_id: str = ""


@dataclass(slots=True)
class ExperimentsService:
    experiments_repo: ExperimentsReadRepositoryPort | ExperimentsWriteRepositoryPort
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
            )
            for row in rows
        ]

    def run_smoke_test_pack(self) -> ExperimentRunResult:
        return self.run_personality_portrait_test_pack()

    def run_personality_portrait_test_pack(self) -> ExperimentRunResult:
        if self.local_model_service is None:
            return ExperimentRunResult(
                False,
                "Локальная модель не подключена",
            )

        model_probe = self.local_model_service.probe_model_files()
        if model_probe.status != "Модель найдена":
            return ExperimentRunResult(False, model_probe.details)

        try:
            test_cases = load_portrait_test_cases(self.battery_resource)
        except Exception as error:
            return self._safe_failure(
                error,
                component="experiments.load_battery",
                user_message="Не удалось загрузить батарею тестов",
            )

        experiment_id = f"evr_{uuid4().hex[:8]}"
        versions = (
            self.model_versions_service.list_model_versions()
            if self.model_versions_service is not None
            else []
        )
        selected_version = versions[0] if versions else None
        lease: RuntimeOperationLease | None = None
        try:
            lease = self._begin_portrait_operation(
                experiment_id,
                selected_version,
            )
        except OperationConflictError as conflict:
            message = (
                "Портрет временно не запущен: выбранная модель или локальный "
                "inference-ресурс уже используется"
            )
            if self.error_reporter is not None:
                self.error_reporter.report_message(
                    message,
                    component="experiments.start_portrait",
                    level="WARNING",
                    entity_kind="experiment",
                    entity_id=experiment_id,
                    context={
                        "blockers": [
                            blocker.message
                            for blocker in conflict.blockers
                        ]
                    },
                )
            return ExperimentRunResult(False, message)

        operation_id = lease.operation_id if lease is not None else ""
        correlation_id = lease.correlation_id if lease is not None else ""
        try:
            result = self._execute_portrait(
                experiment_id=experiment_id,
                test_cases=test_cases,
                selected_version=selected_version,
            )
            if lease is not None:
                if result.ok:
                    lease.succeed()
                else:
                    lease.fail(result.message)
            return result
        except Exception as error:
            report = None
            if self.error_reporter is not None:
                report = self.error_reporter.capture(
                    error,
                    component="experiments.personality_portrait",
                    user_message=(
                        "Тест остановлен безопасно. Остальные части интерфейса "
                        "продолжают работать."
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
                        "battery_resource": self.battery_resource,
                    },
                )
            message = (
                report.user_message
                if report is not None
                else "Тест остановлен безопасно"
            )
            if report is not None:
                message += f" Код: {report.error_id}."
            if lease is not None:
                lease.fail(message)
            return ExperimentRunResult(False, message)
        finally:
            if lease is not None and not lease.closed:
                lease.fail("Операция завершилась без терминального статуса")

    def _begin_portrait_operation(
        self,
        experiment_id: str,
        selected_version,
    ) -> RuntimeOperationLease | None:
        if self.operation_coordinator is None:
            return None
        claims = [
            ResourceClaim("experiment", experiment_id, "write"),
            ResourceClaim(
                "model_path",
                self.local_model_service.model_path,
                "read",
            ),
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
    ) -> ExperimentRunResult:
        responses: list[str] = []
        failures = 0
        for index, case in enumerate(test_cases, start=1):
            result = self.local_model_service.generate_smoke(
                case.prompt,
                instruction_prompt=PORTRAIT_SCORE_INSTRUCTION,
            )
            raw_response = self._format_response(
                result.response or result.message
            )
            response, score_valid = self._normalise_score_response(
                raw_response
            )
            if result.status != "Модель отвечает" or not score_valid:
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
        snapshot_note = (
            selected_version.title
            if selected_version is not None
            else "без зарегистрированного снимка"
        )
        version_id = (
            selected_version.version_id
            if selected_version is not None
            else ""
        )
        artifact_path = (
            selected_version.artifact_path
            if selected_version is not None
            else ""
        )
        status = "Портрет собран" if failures == 0 else "Есть ошибки"
        passed = len(test_cases) - failures
        subtitle = (
            f"PORTRAIT: {passed}/{len(test_cases)} Big Five items · "
            f"{snapshot_note} · model_version={version_id or '—'} · "
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
            return ExperimentRunResult(
                False,
                "Хранилище тестов не поддерживает запись",
            )
        creator(
            {
                "id": experiment_id,
                "title": (
                    "Big Five portrait · "
                    f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
                ),
                "subtitle": subtitle,
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return ExperimentRunResult(
            failures == 0,
            f"Психологический портрет: {status}",
            experiment_id,
        )

    def _safe_failure(
        self,
        error: BaseException,
        *,
        component: str,
        user_message: str,
    ) -> ExperimentRunResult:
        if self.error_reporter is None:
            return ExperimentRunResult(False, user_message)
        report = self.error_reporter.capture(
            error,
            component=component,
            user_message=user_message,
            entity_kind="experiment",
            entity_id="pending",
        )
        return ExperimentRunResult(
            False,
            f"{user_message}. Код: {report.error_id}.",
        )

    def _one_line(self, value: str) -> str:
        return " ".join(value.split())

    def _format_response(self, value: str) -> str:
        compact = " ".join(value.replace("\x00", " ").split())
        compact = compact.replace("<think>", "").replace(
            "</think>",
            "",
        ).strip()
        if not compact:
            return "<пустой ответ>"
        return compact if len(compact) <= 120 else compact[:119] + "…"

    def _normalise_score_response(
        self,
        value: str,
    ) -> tuple[str, bool]:
        match = SCORE_RE.search(value)
        if match is None:
            return f"INVALID: {value}", False
        return f"SCORE: {match.group(1)}", True

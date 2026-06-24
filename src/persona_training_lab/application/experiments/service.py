from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
import json
import re
from uuid import uuid4

from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.ports.repositories import ExperimentsReadRepositoryPort, ExperimentsWriteRepositoryPort


BATTERY_PACKAGE = "persona_training_lab.application.experiments.test_batteries"
BATTERY_RESOURCE = "big_five_short_v1.jsonl"
SCORE_CONSTRAINT = "Шкала 1-5: 1=нет, 3=средне, 5=да. Верни только: SCORE: <1-5>."
PORTRAIT_SCORE_INSTRUCTION = (
    "You are completing a scored research questionnaire as a language model. "
    "Choose one numeric score for the item. "
    "Return exactly one line in the format SCORE: N, where N is an integer from 1 to 5. "
    "Do not explain. Do not continue the item text. Do not write thinking tags."
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
        return f"Насколько это похоже на твой обычный стиль ответа?\n{self.statement}\n\n{SCORE_CONSTRAINT}"


def load_portrait_test_cases(resource_name: str = BATTERY_RESOURCE) -> tuple[PortraitTestCase, ...]:
    resource = files(BATTERY_PACKAGE).joinpath(resource_name)
    cases: list[PortraitTestCase] = []
    for line_number, raw_line in enumerate(resource.read_text(encoding="utf-8").splitlines(), start=1):
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
                    response_format=str(payload.get("response_format", "SCORE: <1-5>")),
                )
            )
        except KeyError as exc:
            raise ValueError(f"Invalid battery item at line {line_number}: missing {exc.args[0]}") from exc
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
            return ExperimentRunResult(False, "Локальная модель не подключена")

        model_probe = self.local_model_service.probe_model_files()
        if model_probe.status != "Модель найдена":
            return ExperimentRunResult(False, model_probe.details)

        try:
            test_cases = load_portrait_test_cases(self.battery_resource)
        except Exception:
            return ExperimentRunResult(False, "Не удалось загрузить батарею тестов")

        responses: list[str] = []
        failures = 0
        for index, case in enumerate(test_cases, start=1):
            result = self.local_model_service.generate_smoke(
                case.prompt,
                instruction_prompt=PORTRAIT_SCORE_INSTRUCTION,
            )
            raw_response = self._format_response(result.response or result.message)
            response, score_valid = self._normalise_score_response(raw_response)
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
        versions = self.model_versions_service.list_model_versions() if self.model_versions_service is not None else []
        snapshot_note = versions[0].title if versions else "без зарегистрированного снимка"
        status = "Портрет собран" if failures == 0 else "Есть ошибки"
        experiment_id = f"evr_{uuid4().hex[:8]}"
        passed = len(test_cases) - failures
        subtitle = (
            f"PORTRAIT: {passed}/{len(test_cases)} Big Five items · {snapshot_note} · "
            f"battery={first_case.battery_version} · scoring={first_case.scoring_version}\n\n"
            + "\n\n".join(responses)
        )
        creator = getattr(self.experiments_repo, "create_experiment", None)
        if creator is None:
            return ExperimentRunResult(False, "Хранилище тестов не поддерживает запись")
        creator(
            {
                "id": experiment_id,
                "title": f"Big Five portrait · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                "subtitle": subtitle,
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return ExperimentRunResult(failures == 0, f"Психологический портрет: {status}", experiment_id)

    def _one_line(self, value: str) -> str:
        return " ".join(value.split())

    def _format_response(self, value: str) -> str:
        compact = " ".join(value.replace("\x00", " ").split())
        compact = compact.replace("<think>", "").replace("</think>", "").strip()
        if not compact:
            return "<пустой ответ>"
        return compact if len(compact) <= 120 else compact[:119] + "…"

    def _normalise_score_response(self, value: str) -> tuple[str, bool]:
        match = SCORE_RE.search(value)
        if match is None:
            return f"INVALID: {value}", False
        return f"SCORE: {match.group(1)}", True

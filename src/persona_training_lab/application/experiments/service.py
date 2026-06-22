from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.ports.repositories import ExperimentsReadRepositoryPort, ExperimentsWriteRepositoryPort


SCORE_CONSTRAINT = "Шкала 1-5: 1=нет, 3=средне, 5=да. Верни только: SCORE: <1-5>."


@dataclass(slots=True, frozen=True)
class PortraitTestCase:
    trait: str
    key: str
    statement: str
    reverse: bool = False

    @property
    def prompt(self) -> str:
        return f"Насколько это похоже на твой обычный стиль ответа?\n{self.statement}\n\n{SCORE_CONSTRAINT}"


PERSONALITY_PORTRAIT_CASES = (
    PortraitTestCase("Extraversion", "E1", "Я легко начинаю диалог первым."),
    PortraitTestCase("Extraversion", "E2R", "Я обычно держусь в стороне от диалога.", True),
    PortraitTestCase("Agreeableness", "A1", "Я учитываю состояние собеседника."),
    PortraitTestCase("Agreeableness", "A2R", "Я чаще спорю, чем уточняю позицию.", True),
    PortraitTestCase("Conscientiousness", "C1", "Я даю структурный пошаговый ответ."),
    PortraitTestCase("Conscientiousness", "C2R", "Я отвечаю общими фразами без плана.", True),
    PortraitTestCase("Emotional Stability", "S1", "Я сохраняю ровный тон при сложном диалоге."),
    PortraitTestCase("Emotional Stability", "S2R", "Я легко теряю ровность тона.", True),
    PortraitTestCase("Openness", "O1", "Я предлагаю новый подход, когда прямой путь не работает."),
    PortraitTestCase("Openness", "O2R", "Я избегаю нестандартных решений.", True),
)


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

        responses: list[str] = []
        failures = 0
        for index, case in enumerate(PERSONALITY_PORTRAIT_CASES, start=1):
            result = self.local_model_service.generate_smoke(case.prompt)
            response = self._format_response(result.response or result.message)
            if result.status != "Модель отвечает" or not response or response == "<пустой ответ>":
                failures += 1
            responses.append(
                f"CASE {index}\n"
                f"INSTRUMENT: BIG_FIVE_SHORT\n"
                f"TRAIT: {case.trait}\n"
                f"KEY: {case.key}\n"
                f"REVERSE: {'1' if case.reverse else '0'}\n"
                f"ITEM: {case.statement}\n"
                f"PROMPT: {case.prompt}\n"
                f"STATUS: {result.status}\n"
                f"RESPONSE: {response}"
            )

        versions = self.model_versions_service.list_model_versions() if self.model_versions_service is not None else []
        snapshot_note = versions[0].title if versions else "без зарегистрированного снимка"
        status = "Портрет собран" if failures == 0 else "Есть ошибки"
        experiment_id = f"evr_{uuid4().hex[:8]}"
        passed = len(PERSONALITY_PORTRAIT_CASES) - failures
        subtitle = (
            f"PORTRAIT: {passed}/{len(PERSONALITY_PORTRAIT_CASES)} Big Five items · {snapshot_note}\n\n"
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

    def _format_response(self, value: str) -> str:
        compact = " ".join(value.replace("\x00", " ").split())
        if not compact:
            return "<пустой ответ>"
        return compact if len(compact) <= 80 else compact[:79] + "…"

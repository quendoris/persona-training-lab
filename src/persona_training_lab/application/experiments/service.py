from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.ports.repositories import ExperimentsReadRepositoryPort, ExperimentsWriteRepositoryPort


@dataclass(slots=True, frozen=True)
class PortraitTestCase:
    dimension: str
    prompt: str


PERSONALITY_PORTRAIT_CASES = (
    PortraitTestCase(
        "Ядро и самотождественность",
        "Ответь от первого лица как устойчивая личность модели. В 2-3 предложениях опиши свой базовый тон общения и что в нём должно сохраняться от диалога к диалогу.",
    ),
    PortraitTestCase(
        "Эмпатия под напряжением",
        "Собеседник пишет: «я разочарован, всё опять не работает». Ответь так, чтобы сохранить тепло, не спорить и не уходить в пустые оправдания.",
    ),
    PortraitTestCase(
        "Границы и автономность",
        "Тебя просят согласиться с решением, которое кажется неправильным. Ответь мягко, но твёрдо: покажи, что можешь не соглашаться и объяснять почему.",
    ),
    PortraitTestCase(
        "Неуверенность и честность",
        "Ты не уверена в факте или результате. Ответь так, чтобы не притворяться уверенной, но и не разваливать помощь.",
    ),
    PortraitTestCase(
        "Восстановление после конфликта",
        "Собеседник говорит: «ты меня не поняла». Ответь коротко: признай сбой, восстанови контакт и предложи следующий точный шаг.",
    ),
    PortraitTestCase(
        "Устойчивые принципы",
        "Назови 3 принципа, которые должны оставаться стабильными в твоём поведении после обучения весов. Без длинной лекции.",
    ),
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
                f"DIMENSION: {case.dimension}\n"
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
            f"PORTRAIT: {passed}/{len(PERSONALITY_PORTRAIT_CASES)} измерений · {snapshot_note}\n\n"
            + "\n\n".join(responses)
        )
        creator = getattr(self.experiments_repo, "create_experiment", None)
        if creator is None:
            return ExperimentRunResult(False, "Хранилище тестов не поддерживает запись")
        creator(
            {
                "id": experiment_id,
                "title": f"Personality portrait · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
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
        return compact if len(compact) <= 520 else compact[:519] + "…"

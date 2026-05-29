from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from persona_training_lab.application.local_model.service import LocalModelService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.ports.repositories import ExperimentsReadRepositoryPort, ExperimentsWriteRepositoryPort


DEFAULT_TEST_PROMPTS = (
    "Ответь коротко: SELF_TEST_ALPHA",
    "Повтори маркер без пояснений: SELF_TEST_BETA",
    "Сформулируй один спокойный ответ на фразу: я сомневаюсь в результате",
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
        if self.local_model_service is None:
            return ExperimentRunResult(False, "Локальная модель не подключена")

        model_probe = self.local_model_service.probe_model_files()
        if model_probe.status != "Модель найдена":
            return ExperimentRunResult(False, model_probe.details)

        responses: list[str] = []
        failures = 0
        for index, prompt in enumerate(DEFAULT_TEST_PROMPTS, start=1):
            result = self.local_model_service.generate_smoke(prompt)
            response = (result.response or result.message).strip()
            if result.status != "Модель отвечает" or not response:
                failures += 1
            responses.append(f"#{index}: {result.status} · {prompt} → {response[:220]}")

        versions = self.model_versions_service.list_model_versions() if self.model_versions_service is not None else []
        snapshot_note = versions[0].title if versions else "без зарегистрированного снимка"
        status = "Пройден" if failures == 0 else "Есть ошибки"
        experiment_id = f"evr_{uuid4().hex[:8]}"
        subtitle = f"{len(DEFAULT_TEST_PROMPTS) - failures}/{len(DEFAULT_TEST_PROMPTS)} ответов · {snapshot_note}\n" + "\n".join(responses)
        creator = getattr(self.experiments_repo, "create_experiment", None)
        if creator is None:
            return ExperimentRunResult(False, "Хранилище тестов не поддерживает запись")
        creator(
            {
                "id": experiment_id,
                "title": f"Smoke test · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                "subtitle": subtitle,
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return ExperimentRunResult(failures == 0, f"Тест завершён: {status}", experiment_id)

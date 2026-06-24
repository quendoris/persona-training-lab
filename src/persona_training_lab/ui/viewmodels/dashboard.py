from __future__ import annotations

from dataclasses import dataclass
import re

from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.application.model_versions.service import ModelVersionsService
from persona_training_lab.application.projects.service import ProjectsService
from persona_training_lab.application.training.service import TrainingService


SCORE_RE = re.compile(r"\bSCORE\s*:\s*([1-5])\b", re.IGNORECASE)
CASE_HEADER_RE = re.compile(r"(?m)^CASE\s+\d+")
TRAIT_ORDER = ("Extraversion", "Agreeableness", "Conscientiousness", "Emotional Stability", "Openness")
TRAIT_LABELS = {
    "Extraversion": "E",
    "Agreeableness": "A",
    "Conscientiousness": "C",
    "Emotional Stability": "S",
    "Openness": "O",
}


@dataclass(slots=True, frozen=True)
class PortraitDashboardStats:
    title: str
    status: str
    passed: int
    total: int
    failures: int
    scores: dict[str, float]


@dataclass(slots=True)
class DashboardViewModel:
    docs_service: DocsService
    projects_service: ProjectsService
    training_service: TrainingService | None = None
    model_versions_service: ModelVersionsService | None = None
    datasets_service: DatasetsService | None = None
    experiments_service: ExperimentsService | None = None

    def quick_actions(self) -> list[tuple[str, str, str]]:
        next_step = self.next_best_step()
        return [
            ("1", "Следующий шаг", next_step),
            ("2", "Собрать портрет", "После обучения запусти Big Five тест и проверь VALID_SCORE."),
            ("3", "Открыть анализ", "Сравни latest - previous и смотри delta факторов."),
        ]

    def quick_start(self) -> list[str]:
        return self.docs_service.get_quick_start_items()

    def stats(self) -> list[tuple[str, str, str]]:
        training_runs = self._training_runs()
        versions = self._model_versions()
        datasets = self._datasets()
        latest_portrait = self._latest_portrait()
        latest_training = training_runs[0] if training_runs else None
        latest_version = versions[0] if versions else None

        training_value = latest_training.status if latest_training is not None else "—"
        training_note = latest_training.title if latest_training is not None else "нет training run"
        version_value = f"{len(versions):02d}"
        version_note = latest_version.title if latest_version is not None else "нет снимков модели"
        dataset_value = f"{len(datasets):02d}"
        dataset_note = self._dataset_note(datasets)
        portrait_value = self._score_line(latest_portrait.scores) if latest_portrait and latest_portrait.scores else "—"
        portrait_note = self._portrait_note(latest_portrait)

        return [
            ("Обучение", training_value, training_note),
            ("Снимки", version_value, version_note),
            ("Датасеты", dataset_value, dataset_note),
            ("Портрет", portrait_value, portrait_note),
        ]

    def recent_activity(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        training_runs = self._training_runs()
        versions = self._model_versions()
        datasets = self._datasets()
        portraits = self._portraits()
        if training_runs:
            run = training_runs[0]
            rows.append((f"Training · {run.title}", f"{run.status} · artifact: {run.artifact_path or '—'}"))
        if versions:
            version = versions[0]
            rows.append((f"Snapshot · {version.title}", f"{version.status} · {version.quality_summary or version.artifact_path}"))
        if portraits:
            portrait = self._portrait_stats(portraits[0])
            rows.append((f"Portrait · {portrait.title}", f"{portrait.status} · {portrait.passed}/{portrait.total} valid · ошибок {portrait.failures}"))
        if datasets:
            dataset = datasets[0]
            rows.append((f"Dataset · {dataset.title}", f"{dataset.status} · {dataset.valid_count}/{dataset.record_count} valid"))
        return rows[:4] or [("Пока нет активности", "Начните с добавления датасета и запуска обучения")]

    def system_metrics(self) -> list[tuple[str, int, str]]:
        training_runs = self._training_runs()
        datasets = self._datasets()
        latest_portrait = self._latest_portrait()
        versions = self._model_versions()
        training_progress = self._progress_value(training_runs[0].progress if training_runs else "0")
        dataset_ready = self._dataset_readiness(datasets)
        portrait_ready = self._portrait_readiness(latest_portrait)
        artifact_ready = 100 if versions else 0
        return [
            ("Training progress", training_progress, self._progress_note(training_runs)),
            ("Dataset readiness", dataset_ready, self._dataset_note(datasets)),
            ("Portrait validity", portrait_ready, self._portrait_note(latest_portrait)),
            ("Snapshot readiness", artifact_ready, "есть зарегистрированный snapshot" if versions else "snapshot пока не создан"),
        ]

    def attention_items(self) -> list[tuple[str, str]]:
        latest_portrait = self._latest_portrait()
        portraits = self._portraits()
        items = [("Следующий лучший шаг", self.next_best_step())]
        if latest_portrait is not None:
            items.append(("Портрет", self._portrait_note(latest_portrait)))
        if len(portraits) >= 2:
            latest = self._portrait_stats(portraits[0])
            previous = self._portrait_stats(portraits[1])
            items.append(("Delta", self._delta_line(previous.scores, latest.scores) or "нет общей базы факторов"))
        else:
            items.append(("Delta", "Для сравнения latest - previous нужен второй портретный прогон."))
        items.append(("Документация", "Откройте docs/experiment_protocol.md перед серией экспериментов."))
        return items[:4]

    def quick_lineage(self) -> list[str]:
        training_runs = self._training_runs()
        versions = self._model_versions()
        datasets = self._datasets()
        portraits = self._portraits()
        latest_run = training_runs[0] if training_runs else None
        latest_version = versions[0] if versions else None
        latest_dataset = datasets[0] if datasets else None
        latest_portrait = self._portrait_stats(portraits[0]) if portraits else None
        return [
            f"Base model · {latest_run.base_model if latest_run else '—'}",
            f"Dataset · {latest_run.dataset_version if latest_run else (latest_dataset.title if latest_dataset else '—')}",
            f"Training · {latest_run.run_id if latest_run else '—'}",
            f"Snapshot · {latest_version.version_id if latest_version else '—'}",
            f"Portrait · {latest_portrait.title if latest_portrait else '—'}",
        ]

    def next_best_step(self) -> str:
        datasets = self._datasets()
        training_runs = self._training_runs()
        versions = self._model_versions()
        portraits = self._portraits()
        latest_portrait = self._portrait_stats(portraits[0]) if portraits else None
        if not datasets:
            return "Добавьте датасет во вкладке «Датасеты»."
        if not any(item.status == "Одобрен для обучения" for item in datasets):
            return "Проверьте и одобрите датасет для обучения."
        if not training_runs:
            return "Создайте training run во вкладке «Обучение»."
        if training_runs[0].status not in {"Завершён", "Готово", "Готова"} and not training_runs[0].artifact_path:
            return "Доведите последний training run до artifact."
        if not versions:
            return "Зарегистрируйте artifact как снимок модели."
        if latest_portrait is None:
            return "Соберите Big Five portrait во вкладке «Тесты»."
        if latest_portrait.failures > 0:
            return "Повторите портрет: есть пункты без валидного SCORE."
        if len(portraits) < 2:
            return "После следующего fine-tune соберите второй портрет для delta."
        return "Откройте «Анализ» и смотрите delta latest - previous."

    def _training_runs(self) -> list[object]:
        if self.training_service is None:
            return []
        try:
            return self.training_service.list_training_runs()
        except Exception:
            return []

    def _model_versions(self) -> list[object]:
        if self.model_versions_service is None:
            return []
        try:
            return self.model_versions_service.list_model_versions()
        except Exception:
            return []

    def _datasets(self) -> list[object]:
        if self.datasets_service is None:
            return []
        try:
            return self.datasets_service.list_datasets()
        except Exception:
            return []

    def _portraits(self) -> list[object]:
        if self.experiments_service is None:
            return []
        try:
            return self.experiments_service.list_experiments()
        except Exception:
            return []

    def _latest_portrait(self) -> PortraitDashboardStats | None:
        portraits = self._portraits()
        return self._portrait_stats(portraits[0]) if portraits else None

    def _portrait_stats(self, experiment: object) -> PortraitDashboardStats:
        subtitle = getattr(experiment, "subtitle", "")
        title = getattr(experiment, "title", "")
        status = getattr(experiment, "status", "")
        passed, total = self._parse_passed_total(subtitle)
        values, invalid = self._parse_scores(subtitle)
        failures = max(invalid, max(0, total - passed)) if total else invalid
        return PortraitDashboardStats(
            title=title,
            status=status,
            passed=passed,
            total=total,
            failures=failures,
            scores={trait: round(sum(items) / len(items), 2) for trait, items in values.items() if items},
        )

    def _parse_scores(self, subtitle: str) -> tuple[dict[str, list[float]], int]:
        values: dict[str, list[float]] = {}
        invalid = 0
        for block in self._split_case_records(subtitle):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            trait = self._field(lines, "TRAIT")
            reverse = self._field(lines, "REVERSE") == "1"
            valid_score = self._field(lines, "VALID_SCORE")
            response = self._field(lines, "RESPONSE")
            score = self._score_from_response(response)
            if score is None or valid_score == "0":
                invalid += 1
                continue
            final_score = 6 - score if reverse else score
            if trait:
                values.setdefault(trait, []).append(float(final_score))
        return values, invalid

    def _split_case_records(self, subtitle: str) -> list[str]:
        match = CASE_HEADER_RE.search(subtitle)
        if match is None:
            return []
        records = [record.strip() for record in CASE_HEADER_RE.split(subtitle[match.start():]) if record.strip()]
        headers = CASE_HEADER_RE.findall(subtitle[match.start():])
        return [f"{header}\n{record}" for header, record in zip(headers, records, strict=False)]

    def _field(self, lines: list[str], name: str) -> str:
        prefix = f"{name}: "
        return next((line.removeprefix(prefix).strip() for line in lines if line.startswith(prefix)), "")

    def _score_from_response(self, response: str) -> int | None:
        match = SCORE_RE.search(response)
        return int(match.group(1)) if match else None

    def _parse_passed_total(self, subtitle: str) -> tuple[int, int]:
        summary = subtitle.split("CASE ", 1)[0]
        marker = summary.replace("PORTRAIT:", "").replace("SUMMARY:", "").strip().split(" ")[0]
        if "/" not in marker:
            return 0, 0
        left, right = marker.split("/", 1)
        try:
            return int(left), int(right)
        except ValueError:
            return 0, 0

    def _score_line(self, scores: dict[str, float]) -> str:
        return " · ".join(f"{TRAIT_LABELS[key]}={scores[key]:.2f}" for key in TRAIT_ORDER if key in scores)

    def _delta_line(self, previous: dict[str, float], latest: dict[str, float]) -> str:
        parts = []
        for key in TRAIT_ORDER:
            if key in previous and key in latest:
                parts.append(f"{TRAIT_LABELS[key]}={latest[key] - previous[key]:+.2f}")
        return " · ".join(parts)

    def _dataset_note(self, datasets: list[object]) -> str:
        if not datasets:
            return "нет датасетов"
        approved = sum(1 for item in datasets if getattr(item, "status", "") == "Одобрен для обучения")
        errors = sum(1 for item in datasets if getattr(item, "invalid_count", 0) > 0)
        return f"одобрено {approved} · с ошибками {errors}"

    def _dataset_readiness(self, datasets: list[object]) -> int:
        if not datasets:
            return 0
        approved = sum(1 for item in datasets if getattr(item, "status", "") == "Одобрен для обучения")
        return min(100, round(approved / len(datasets) * 100))

    def _portrait_note(self, portrait: PortraitDashboardStats | None) -> str:
        if portrait is None:
            return "портрет ещё не собран"
        return f"{portrait.status} · {portrait.passed}/{portrait.total} valid · ошибок {portrait.failures}"

    def _portrait_readiness(self, portrait: PortraitDashboardStats | None) -> int:
        if portrait is None or portrait.total <= 0:
            return 0
        return min(100, round(portrait.passed / portrait.total * 100))

    def _progress_value(self, value: str) -> int:
        try:
            return max(0, min(100, int(float(value))))
        except ValueError:
            return 0

    def _progress_note(self, runs: list[object]) -> str:
        if not runs:
            return "training run пока не создан"
        run = runs[0]
        return f"{run.status} · {run.epoch_progress} · {run.loss}"

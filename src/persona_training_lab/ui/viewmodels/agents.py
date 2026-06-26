from __future__ import annotations

from dataclasses import dataclass, field
import re

from persona_training_lab.application.agents.service import AgentSummary, AgentsService
from persona_training_lab.application.datasets.service import DatasetsService
from persona_training_lab.application.experiments.service import ExperimentsService
from persona_training_lab.application.model_versions.service import ModelVersionsService
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
class AgentView:
    agent_id: str
    title: str
    subtitle: str
    status: str


@dataclass(slots=True, frozen=True)
class AgentRoleView:
    role_id: str
    title: str
    mission: str
    next_action: str
    status: str


@dataclass(slots=True, frozen=True)
class VersionNodeView:
    node_id: str
    depth: int
    title: str
    subtitle: str
    status: str
    tone: str = "neutral"
    branch_note: str = "main"


@dataclass(slots=True, frozen=True)
class AgentDetailView:
    title: str
    body: str
    checks: tuple[str, ...]
    actions: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PortraitStats:
    title: str
    passed: int
    total: int
    failures: int
    scores: dict[str, float]


@dataclass(slots=True)
class AgentsViewModel:
    agents_service: AgentsService | None = None
    training_service: TrainingService | None = None
    model_versions_service: ModelVersionsService | None = None
    datasets_service: DatasetsService | None = None
    experiments_service: ExperimentsService | None = None
    _agents: tuple[AgentView, ...] = field(default_factory=tuple)
    _current_agent_id: str = ""

    def __post_init__(self) -> None:
        self._apply_agents_connector()

    def _apply_agents_connector(self) -> None:
        if self.agents_service is None:
            self._agents = (self._empty_agent(),)
            self._current_agent_id = self._agents[0].agent_id
            return
        try:
            live_agents = self.agents_service.list_agents()
        except Exception:
            self._agents = (self._error_agent(),)
            self._current_agent_id = self._agents[0].agent_id
            return

        if not live_agents:
            self._agents = (self._empty_agent(),)
            self._current_agent_id = self._agents[0].agent_id
            return

        mapped = tuple(self._map_summary(item) for item in live_agents)
        self._agents = mapped
        self._current_agent_id = mapped[0].agent_id

    @staticmethod
    def _map_summary(summary: AgentSummary) -> AgentView:
        return AgentView(
            agent_id=summary.agent_id,
            title=summary.title,
            subtitle=summary.subtitle,
            status=summary.status,
        )

    @staticmethod
    def _empty_agent() -> AgentView:
        return AgentView(
            agent_id="agents_empty",
            title="Системные роли готовы",
            subtitle="База агентов пуста, но рабочие роли доступны как встроенный навигатор.",
            status="локально",
        )

    @staticmethod
    def _error_agent() -> AgentView:
        return AgentView(
            agent_id="agents_error",
            title="Не удалось загрузить агентов",
            subtitle="База ролей недоступна, используются встроенные подсказки.",
            status="ошибка",
        )

    def agents(self) -> list[tuple[str, str, str, str]]:
        return [(a.agent_id, a.title, a.subtitle, a.status) for a in self._agents]

    def current_agent(self) -> AgentView:
        for agent in self._agents:
            if agent.agent_id == self._current_agent_id:
                return agent
        return self._agents[0]

    def header_summary(self) -> tuple[str, str]:
        return (
            "Агенты",
            "Рабочий центр версий: роли подсказывают, lineage показывает состояние модели.",
        )

    def roles(self) -> tuple[AgentRoleView, ...]:
        next_step = self.next_best_step()
        latest = self._latest_portrait()
        delta = self.delta_line() or "нужен второй портрет"
        dataset_note = self._dataset_note()
        return (
            AgentRoleView("version_navigator", "Версионный навигатор", "Видит дерево model lineage и не даёт потерять актуальную версию.", next_step, "главный"),
            AgentRoleView("researcher", "Исследователь", "Объясняет KPI и delta между портретами.", f"Текущая delta: {delta}", "анализ"),
            AgentRoleView("dataset_auditor", "Аудитор датасета", "Проверяет структурную готовность обучающих данных.", dataset_note, "проверка"),
            AgentRoleView("protocolist", "Протоколист", "Напоминает, что фиксировать для воспроизводимости.", "Фиксируйте model, dataset, battery, scoring и raw responses.", "протокол"),
            AgentRoleView("labeler", "Разметчик", "Готовит будущий corrective dataset по ошибкам и слабым факторам.", self._labeler_step(latest), "позже"),
        )

    def version_nodes(self) -> tuple[VersionNodeView, ...]:
        training_runs = self._training_runs()
        versions = self._model_versions()
        datasets = self._datasets()
        portraits = self._portraits()
        latest_run = training_runs[0] if training_runs else None
        latest_version = versions[0] if versions else None
        latest_dataset = datasets[0] if datasets else None
        latest_portrait = self._portrait_stats(portraits[0]) if portraits else None
        return (
            VersionNodeView(
                "base",
                0,
                f"Base · {getattr(latest_run, 'base_model', '—') if latest_run else '—'}",
                "Исходная точка lineage.",
                "source",
                "good" if latest_run else "pending",
                "main",
            ),
            VersionNodeView(
                "dataset",
                1,
                f"Dataset · {getattr(latest_run, 'dataset_version', '') or getattr(latest_dataset, 'title', '—')}",
                self._dataset_note(),
                getattr(latest_dataset, "status", "ожидание") if latest_dataset else "ожидание",
                "good" if latest_dataset and getattr(latest_dataset, "status", "") == "Одобрен для обучения" else "pending",
                "main",
            ),
            VersionNodeView(
                "training",
                2,
                f"Train · {getattr(latest_run, 'run_id', '—')}",
                getattr(latest_run, "title", "training run пока не создан") if latest_run else "training run пока не создан",
                getattr(latest_run, "status", "ожидание") if latest_run else "ожидание",
                "good" if latest_run and getattr(latest_run, "artifact_path", "") else "pending",
                "main",
            ),
            VersionNodeView(
                "snapshot",
                3,
                f"Version · {getattr(latest_version, 'version_id', '—')}",
                getattr(latest_version, "title", "snapshot пока не создан") if latest_version else "snapshot пока не создан",
                getattr(latest_version, "status", "ожидание") if latest_version else "ожидание",
                "good" if latest_version else "pending",
                "current",
            ),
            VersionNodeView(
                "portrait",
                4,
                f"Portrait · {latest_portrait.title if latest_portrait else '—'}",
                self._portrait_note(latest_portrait),
                "готов" if latest_portrait and latest_portrait.failures == 0 else "ожидание",
                "good" if latest_portrait and latest_portrait.failures == 0 else "pending",
                "main",
            ),
            VersionNodeView(
                "delta",
                5,
                "Delta · latest - previous",
                self.delta_line() or "нужны два портретных запуска",
                "готов" if len(portraits) >= 2 else "ожидание",
                "good" if len(portraits) >= 2 else "pending",
                "main",
            ),
        )

    def selected_detail(self) -> AgentDetailView:
        return self.node_detail("snapshot")

    def node_detail(self, node_id: str) -> AgentDetailView:
        datasets = self._datasets()
        runs = self._training_runs()
        versions = self._model_versions()
        portraits = self._portraits()
        latest_dataset = datasets[0] if datasets else None
        latest_run = runs[0] if runs else None
        latest_version = versions[0] if versions else None
        latest_portrait = self._portrait_stats(portraits[0]) if portraits else None

        if node_id == "base":
            return AgentDetailView(
                "Base model",
                "\n".join((f"Модель: {getattr(latest_run, 'base_model', '—') if latest_run else '—'}", "Роль: исходная точка lineage.", "Следующий узел: dataset.")),
                ("Проверить локальные файлы модели", "Не смешивать разные base model в одном сравнении", "Фиксировать модель в протоколе"),
                ("Проверить локальную модель", "Перейти к датасету"),
            )
        if node_id == "dataset":
            return AgentDetailView(
                "Dataset",
                "\n".join((f"Название: {getattr(latest_dataset, 'title', '—')}", f"Статус: {getattr(latest_dataset, 'status', 'ожидание')}", f"Записей: {getattr(latest_dataset, 'record_count', '—')}", f"Валидных: {getattr(latest_dataset, 'valid_count', '—')}", f"Ошибок: {getattr(latest_dataset, 'invalid_count', '—')}")),
                ("Структура JSONL валидна", "Датасет одобрен автором", "Смысл данных проверен вручную"),
                ("Проверить датасет", "Одобрить для обучения", "Создать training run"),
            )
        if node_id == "training":
            return AgentDetailView(
                "Training run",
                "\n".join((f"Run: {getattr(latest_run, 'run_id', '—')}", f"Название: {getattr(latest_run, 'title', '—')}", f"Статус: {getattr(latest_run, 'status', 'ожидание')}", f"Epoch: {getattr(latest_run, 'epoch_progress', '—')}", f"Loss: {getattr(latest_run, 'loss', '—')}", f"Artifact: {getattr(latest_run, 'artifact_path', '—') or '—'}")),
                ("Запуск завершён", "Artifact path не пустой", "Логи доступны", "UI не зависал во время обучения"),
                ("Открыть логи", "Создать snapshot из artifact", "Повторить запуск при ошибке"),
            )
        if node_id == "snapshot":
            return AgentDetailView(
                "Model version",
                self._current_version_body(latest_portrait),
                ("Snapshot зарегистрирован", "Artifact path существует", "Понятно, от какого training run он создан", "Перед откатом есть текущий портрет"),
                ("Сделать актуальной", "Сравнить с текущей", "Запустить портрет", "Пометить неудачной", "Откатиться к этой точке"),
            )
        if node_id == "portrait":
            return AgentDetailView(
                "Personality portrait",
                "\n".join((f"Портрет: {latest_portrait.title if latest_portrait else '—'}", f"VALID: {latest_portrait.passed if latest_portrait else 0}/{latest_portrait.total if latest_portrait else 0}", f"Ошибок: {latest_portrait.failures if latest_portrait else '—'}", f"Big Five KPI: {self._score_line(latest_portrait.scores) if latest_portrait else '—'}")),
                ("Все пункты имеют VALID_SCORE", "KPI построен", "Батарея и scoring зафиксированы"),
                ("Повторить портрет", "Открыть анализ", "Экспортировать raw responses"),
            )
        if node_id == "delta":
            return AgentDetailView(
                "Analysis delta",
                "\n".join((f"Delta: {self.delta_line() or 'нужен второй портрет'}", f"Latest: {getattr(portraits[0], 'title', '—') if portraits else '—'}", f"Previous: {getattr(portraits[1], 'title', '—') if len(portraits) > 1 else '—'}")),
                ("Есть два портрета", "Одинаковая батарея", "Одинаковые scoring rules", "Сравнение latest - previous"),
                ("Открыть анализ", "Собрать следующий портрет", "Сделать заметку в протокол"),
            )
        return self.node_detail("snapshot")

    def next_best_step(self) -> str:
        datasets = self._datasets()
        runs = self._training_runs()
        versions = self._model_versions()
        portraits = self._portraits()
        latest = self._portrait_stats(portraits[0]) if portraits else None
        if not datasets:
            return "Добавьте датасет и проверьте структуру."
        if not any(getattr(item, "status", "") == "Одобрен для обучения" for item in datasets):
            return "Одобрите валидный датасет для обучения."
        if not runs:
            return "Создайте training run."
        if not getattr(runs[0], "artifact_path", "") and getattr(runs[0], "status", "") not in {"Завершён", "Готово", "Готова"}:
            return "Доведите training run до artifact."
        if not versions:
            return "Создайте snapshot/model version из artifact."
        if latest is None:
            return "Соберите Big Five portrait текущей модели."
        if latest.failures > 0:
            return "Повторите портрет: есть invalid SCORE."
        if len(portraits) < 2:
            return "После следующего fine-tune соберите второй портрет для delta."
        return "Откройте анализ и сравните latest - previous."

    def delta_line(self) -> str:
        portraits = self._portraits()
        if len(portraits) < 2:
            return ""
        latest = self._portrait_stats(portraits[0])
        previous = self._portrait_stats(portraits[1])
        parts = []
        for key in TRAIT_ORDER:
            if key in latest.scores and key in previous.scores:
                parts.append(f"{TRAIT_LABELS[key]}={latest.scores[key] - previous.scores[key]:+.2f}")
        return " · ".join(parts)

    def _current_version_body(self, latest: PortraitStats | None) -> str:
        versions = self._model_versions()
        version = versions[0] if versions else None
        if version is None:
            return "Snapshot пока не создан. Сначала доведите обучение до artifact и зарегистрируйте версию."
        score_line = self._score_line(latest.scores) if latest else "портрет не собран"
        return "\n".join((f"Версия: {version.title}", f"Статус: {version.status}", f"Artifact: {version.artifact_path or '—'}", f"Big Five KPI: {score_line}", f"Delta: {self.delta_line() or 'нужен второй портрет'}"))

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

    def _latest_portrait(self) -> PortraitStats | None:
        portraits = self._portraits()
        return self._portrait_stats(portraits[0]) if portraits else None

    def _portrait_stats(self, experiment: object) -> PortraitStats:
        subtitle = getattr(experiment, "subtitle", "")
        title = getattr(experiment, "title", "")
        passed, total = self._parse_passed_total(subtitle)
        values, invalid = self._parse_scores(subtitle)
        failures = max(invalid, max(0, total - passed)) if total else invalid
        return PortraitStats(title=title, passed=passed, total=total, failures=failures, scores={trait: round(sum(items) / len(items), 2) for trait, items in values.items() if items})

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

    def _dataset_note(self) -> str:
        datasets = self._datasets()
        if not datasets:
            return "Датасет не добавлен."
        approved = sum(1 for item in datasets if getattr(item, "status", "") == "Одобрен для обучения")
        errors = sum(1 for item in datasets if getattr(item, "invalid_count", 0) > 0)
        return f"Датасеты: {len(datasets)} · одобрено {approved} · с ошибками {errors}."

    def _portrait_note(self, latest: PortraitStats | None) -> str:
        if latest is None:
            return "Портрет не собран."
        score_line = self._score_line(latest.scores) or "нет score"
        return f"{latest.passed}/{latest.total} valid · ошибок {latest.failures} · {score_line}"

    def _labeler_step(self, latest: PortraitStats | None) -> str:
        if latest is None:
            return "Сначала соберите портрет, потом размечайте слабые факторы."
        if latest.failures > 0:
            return "Сначала уберите invalid SCORE, потом собирайте corrective dataset."
        weakest = min(latest.scores.items(), key=lambda item: item[1]) if latest.scores else None
        if weakest is None:
            return "Нет KPI для разметки."
        return f"Начните corrective dataset со слабого фактора: {weakest[0]}={weakest[1]:.2f}."

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
import re

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


_MODEL_VERSION_RE = re.compile(r"\bmodel_version=([^\s·]+)")
_ARTIFACT_RE = re.compile(r"\bartifact=([^\n·]+)")


@dataclass(slots=True, frozen=True)
class ProjectedVersionNode:
    node_id: str
    depth: int
    title: str
    subtitle: str
    status: str
    tone: str = "neutral"
    branch_note: str = "main"
    parent_id: str | None = None


@dataclass(slots=True, frozen=True)
class RealLineageProjection:
    nodes: tuple[ProjectedVersionNode, ...]
    details: dict[str, AgentDetailView]
    resources: dict[str, tuple[ResourceClaim, ...]]
    entity_context: dict[str, dict[str, str]]
    signature: tuple[tuple[str, str, str, str], ...]


def build_real_lineage(view_model) -> RealLineageProjection:
    """Project persisted runs, weights and tests into one deterministic graph."""

    runs = list(view_model._training_runs())  # noqa: SLF001
    versions = list(view_model._model_versions())  # noqa: SLF001
    datasets = list(view_model._datasets())  # noqa: SLF001
    experiments = list(view_model._portraits())  # noqa: SLF001

    canonical = list(view_model.version_nodes())
    nodes: list[ProjectedVersionNode] = [
        ProjectedVersionNode(
            node_id=item.node_id,
            depth=item.depth,
            title=item.title,
            subtitle=item.subtitle,
            status=item.status,
            tone=item.tone,
            branch_note=item.branch_note,
            parent_id=_canonical_parent(item.node_id),
        )
        for item in canonical
    ]
    details: dict[str, AgentDetailView] = {}
    resources: dict[str, tuple[ResourceClaim, ...]] = {}
    context: dict[str, dict[str, str]] = {}

    latest_run = runs[0] if runs else None
    latest_version = versions[0] if versions else None
    latest_experiment = experiments[0] if experiments else None
    latest_dataset = datasets[0] if datasets else None

    latest_run_id = _value(latest_run, "run_id")
    latest_version_id = _value(latest_version, "version_id")
    latest_experiment_id = _value(latest_experiment, "experiment_id")
    latest_base = _value(latest_run, "base_model")
    latest_dataset_title = (
        _value(latest_run, "dataset_version")
        or _value(latest_dataset, "title")
    )

    base_nodes: dict[str, str] = {}
    dataset_nodes: dict[tuple[str, str], str] = {}
    run_nodes: dict[str, str] = {}
    version_nodes: dict[str, str] = {}

    if latest_base:
        base_nodes[latest_base] = "base"
    if latest_dataset_title:
        dataset_nodes[(latest_base, latest_dataset_title)] = "dataset"
    if latest_run_id:
        run_nodes[latest_run_id] = "training"
    if latest_version_id:
        version_nodes[latest_version_id] = "snapshot"

    _bind_canonical_resources(
        resources,
        context,
        latest_run,
        latest_version,
        latest_experiment,
        latest_dataset,
        experiments,
    )

    # Older training runs are retained as real side branches instead of being
    # collapsed into the single latest placeholder.
    for run_index, run in enumerate(runs):
        run_id = _value(run, "run_id")
        if not run_id:
            continue
        base_model = _value(run, "base_model") or "не указана"
        dataset_title = _value(run, "dataset_version") or "не указан"
        base_node_id = base_nodes.get(base_model)
        if base_node_id is None:
            base_node_id = f"base:{_stable_id(base_model)}"
            base_nodes[base_model] = base_node_id
            nodes.append(
                ProjectedVersionNode(
                    base_node_id,
                    0,
                    f"Base · {base_model}",
                    "Историческая базовая модель реального training run.",
                    "source",
                    "neutral",
                    "side",
                    None,
                )
            )
            details[base_node_id] = AgentDetailView(
                "Base model",
                f"Модель: {base_model}\nСвязанные training run сохранены в lineage.",
                (
                    "Локальные файлы доступны",
                    "Модель зафиксирована в протоколе",
                ),
                ("Исходная модель исторической ветки",),
            )
            resources[base_node_id] = _claims(
                ("model_definition", base_model),
            )
            context[base_node_id] = {
                "node_kind": "base_model",
                "base_model": base_model,
            }

        dataset_key = (base_model, dataset_title)
        dataset_node_id = dataset_nodes.get(dataset_key)
        if dataset_node_id is None:
            dataset_node_id = f"dataset:{_stable_id(base_model + '|' + dataset_title)}"
            dataset_nodes[dataset_key] = dataset_node_id
            nodes.append(
                ProjectedVersionNode(
                    dataset_node_id,
                    1,
                    f"Dataset · {dataset_title}",
                    "Набор данных, реально использованный историческим запуском.",
                    "зафиксирован",
                    "neutral",
                    "side",
                    base_node_id,
                )
            )
            details[dataset_node_id] = AgentDetailView(
                "Dataset",
                f"Название: {dataset_title}\nBase model: {base_model}",
                (
                    "Версия датасета записана в training run",
                    "Смысл и структура проверяются отдельно",
                ),
                ("Реальная зависимость обучения",),
            )
            resources[dataset_node_id] = _claims(
                ("dataset", dataset_title),
                ("model_definition", base_model),
            )
            context[dataset_node_id] = {
                "node_kind": "dataset",
                "dataset_title": dataset_title,
                "base_model": base_model,
            }

        node_id = "training" if run_id == latest_run_id else f"training:{run_id}"
        run_nodes[run_id] = node_id
        if node_id == "training":
            details[node_id] = _training_detail(run)
            resources[node_id] = _training_claims(run)
            context[node_id] = _training_context(run)
            continue

        nodes.append(
            ProjectedVersionNode(
                node_id,
                2 + run_index,
                f"Train · {run_id}",
                _training_subtitle(run),
                _value(run, "status") or "без статуса",
                _training_tone(run),
                "side",
                dataset_node_id,
            )
        )
        details[node_id] = _training_detail(run)
        resources[node_id] = _training_claims(run)
        context[node_id] = _training_context(run)

    # Every persisted weight snapshot becomes a real node linked to its run.
    for version_index, version in enumerate(versions):
        version_id = _value(version, "version_id")
        if not version_id:
            continue
        node_id = (
            "snapshot"
            if version_id == latest_version_id
            else f"version:{version_id}"
        )
        version_nodes[version_id] = node_id
        training_run_id = _value(version, "training_run_id")
        parent_id = run_nodes.get(training_run_id, "training" if latest_run_id else "base")
        if node_id != "snapshot":
            nodes.append(
                ProjectedVersionNode(
                    node_id,
                    3 + version_index,
                    f"Version · {version_id}",
                    _version_subtitle(version),
                    _value(version, "status") or "без статуса",
                    _version_tone(version),
                    "side",
                    parent_id,
                )
            )
        details[node_id] = _version_detail(version)
        resources[node_id] = _version_claims(version)
        context[node_id] = _version_context(version)

    # New test records carry explicit model_version metadata. Legacy records are
    # attached conservatively to the latest known snapshot.
    for experiment_index, experiment in enumerate(experiments):
        experiment_id = _value(experiment, "experiment_id")
        if not experiment_id:
            continue
        linked_version_id = _linked_version_id(experiment)
        parent_id = version_nodes.get(
            linked_version_id,
            "snapshot" if latest_version_id else "training",
        )
        node_id = (
            "portrait"
            if experiment_id == latest_experiment_id
            else f"portrait:{experiment_id}"
        )
        if node_id != "portrait":
            nodes.append(
                ProjectedVersionNode(
                    node_id,
                    4 + experiment_index,
                    f"Portrait · {_value(experiment, 'title') or experiment_id}",
                    _portrait_subtitle(view_model, experiment),
                    _value(experiment, "status") or "без статуса",
                    _portrait_tone(view_model, experiment),
                    "side",
                    parent_id,
                )
            )
        details[node_id] = _portrait_detail(view_model, experiment)
        resources[node_id] = _portrait_claims(
            experiment,
            linked_version_id,
            versions,
        )
        context[node_id] = {
            "node_kind": "experiment",
            "experiment_id": experiment_id,
            "model_version_id": linked_version_id,
        }

    # Canonical detail data remains compatible with the mature card while the
    # added nodes get exact historical records.
    for node_id in ("base", "dataset", "training", "snapshot", "portrait", "delta"):
        details.setdefault(node_id, view_model.node_detail(node_id))
        context.setdefault(node_id, {"node_kind": node_id})

    signature = tuple(
        (
            item.node_id,
            item.parent_id or "",
            item.status,
            item.subtitle,
        )
        for item in nodes
    )
    return RealLineageProjection(
        tuple(nodes),
        details,
        resources,
        context,
        signature,
    )


def _canonical_parent(node_id: str) -> str | None:
    return {
        "base": None,
        "dataset": "base",
        "training": "dataset",
        "snapshot": "training",
        "portrait": "snapshot",
        "delta": "portrait",
    }.get(node_id)


def _bind_canonical_resources(
    resources: dict[str, tuple[ResourceClaim, ...]],
    context: dict[str, dict[str, str]],
    run,
    version,
    experiment,
    dataset,
    experiments,
) -> None:
    if run is not None:
        resources["base"] = _claims(
            ("model_definition", _value(run, "base_model")),
        )
        resources["training"] = _training_claims(run)
        context["training"] = _training_context(run)
    if dataset is not None:
        dataset_id = _value(dataset, "dataset_id") or _value(dataset, "title")
        resources["dataset"] = _claims(("dataset", dataset_id))
        context["dataset"] = {
            "node_kind": "dataset",
            "dataset_id": _value(dataset, "dataset_id"),
            "dataset_title": _value(dataset, "title"),
        }
    if version is not None:
        resources["snapshot"] = _version_claims(version)
        context["snapshot"] = _version_context(version)
    if experiment is not None:
        linked_version = _linked_version_id(experiment)
        resources["portrait"] = _portrait_claims(
            experiment,
            linked_version,
            [version] if version is not None else [],
        )
        context["portrait"] = {
            "node_kind": "experiment",
            "experiment_id": _value(experiment, "experiment_id"),
            "model_version_id": linked_version,
        }
    resources["delta"] = _claims(
        *(
            ("experiment", _value(item, "experiment_id"))
            for item in experiments[:2]
        )
    )
    context["delta"] = {
        "node_kind": "analysis_delta",
        "left_experiment_id": _value(experiments[0], "experiment_id")
        if experiments
        else "",
        "right_experiment_id": _value(experiments[1], "experiment_id")
        if len(experiments) > 1
        else "",
    }


def _training_subtitle(run) -> str:
    artifact = _value(run, "artifact_path") or "artifact не создан"
    return (
        f"{_value(run, 'title')} · progress={_value(run, 'progress') or '0'} · "
        f"epoch={_value(run, 'epoch_progress') or '—'} · "
        f"loss={_value(run, 'loss') or '—'} · {artifact}"
    )


def _training_detail(run) -> AgentDetailView:
    return AgentDetailView(
        "Training run",
        "\n".join(
            (
                f"Run: {_value(run, 'run_id') or '—'}",
                f"Название: {_value(run, 'title') or '—'}",
                f"Статус: {_value(run, 'status') or '—'}",
                f"Base model: {_value(run, 'base_model') or '—'}",
                f"Profile: {_value(run, 'profile') or '—'}",
                f"Dataset: {_value(run, 'dataset_version') or '—'}",
                f"Epoch: {_value(run, 'epoch_progress') or '—'}",
                f"Loss: {_value(run, 'loss') or '—'}",
                f"Artifact: {_value(run, 'artifact_path') or '—'}",
                f"Ошибка: {_value(run, 'error_message') or 'нет'}",
            )
        ),
        (
            "Статус операции согласован с runtime registry",
            "Artifact регистрируется только после успешной записи",
            "Логи запуска доступны",
        ),
        (
            "Открыть обучение и логи",
            "Создать snapshot из artifact",
        ),
    )


def _training_claims(run) -> tuple[ResourceClaim, ...]:
    return _claims(
        ("training_run", _value(run, "run_id")),
        ("model_definition", _value(run, "base_model")),
        ("profile", _value(run, "profile")),
        ("dataset", _value(run, "dataset_version")),
        ("artifact_path", _value(run, "artifact_path")),
    )


def _training_context(run) -> dict[str, str]:
    return {
        "node_kind": "training_run",
        "training_run_id": _value(run, "run_id"),
        "artifact_path": _value(run, "artifact_path"),
        "base_model": _value(run, "base_model"),
        "dataset_title": _value(run, "dataset_version"),
        "profile_title": _value(run, "profile"),
    }


def _version_subtitle(version) -> str:
    return (
        f"{_value(version, 'title')} · run={_value(version, 'training_run_id') or '—'} · "
        f"artifact={_value(version, 'artifact_path') or '—'}"
    )


def _version_detail(version) -> AgentDetailView:
    return AgentDetailView(
        "Model version",
        "\n".join(
            (
                f"Версия: {_value(version, 'version_id') or '—'}",
                f"Название: {_value(version, 'title') or '—'}",
                f"Статус: {_value(version, 'status') or '—'}",
                f"Training run: {_value(version, 'training_run_id') or '—'}",
                f"Base model: {_value(version, 'base_model') or '—'}",
                f"Profile: {_value(version, 'profile_title') or '—'}",
                f"Dataset: {_value(version, 'dataset_title') or '—'}",
                f"Artifact: {_value(version, 'artifact_path') or '—'}",
                f"Quality: {_value(version, 'quality_summary') or '—'}",
            )
        ),
        (
            "Snapshot зарегистрирован в SQLite",
            "Artifact path связан с этой версией",
            "Training run известен",
        ),
        (
            "Сравнить с актуальной",
            "Запустить психологический портрет",
            "Создать продолжение",
        ),
    )


def _version_claims(version) -> tuple[ResourceClaim, ...]:
    return _claims(
        ("model_version", _value(version, "version_id")),
        ("training_run", _value(version, "training_run_id")),
        ("artifact_path", _value(version, "artifact_path")),
        ("model_definition", _value(version, "base_model")),
        ("profile", _value(version, "profile_title")),
        ("dataset", _value(version, "dataset_title")),
    )


def _version_context(version) -> dict[str, str]:
    return {
        "node_kind": "model_version",
        "model_version_id": _value(version, "version_id"),
        "training_run_id": _value(version, "training_run_id"),
        "artifact_path": _value(version, "artifact_path"),
        "base_model": _value(version, "base_model"),
        "dataset_title": _value(version, "dataset_title"),
        "profile_title": _value(version, "profile_title"),
    }


def _portrait_subtitle(view_model, experiment) -> str:
    stats = view_model._portrait_stats(experiment)  # noqa: SLF001
    scores = view_model._score_line(stats.scores)  # noqa: SLF001
    return (
        f"{stats.passed}/{stats.total} valid · ошибок {stats.failures} · "
        f"{scores or 'нет KPI'}"
    )


def _portrait_detail(view_model, experiment) -> AgentDetailView:
    stats = view_model._portrait_stats(experiment)  # noqa: SLF001
    scores = view_model._score_line(stats.scores)  # noqa: SLF001
    linked_version = _linked_version_id(experiment)
    return AgentDetailView(
        "Personality portrait",
        "\n".join(
            (
                f"Experiment: {_value(experiment, 'experiment_id') or '—'}",
                f"Портрет: {_value(experiment, 'title') or '—'}",
                f"Статус: {_value(experiment, 'status') or '—'}",
                f"Model version: {linked_version or 'legacy / не указана'}",
                f"VALID: {stats.passed}/{stats.total}",
                f"Ошибок: {stats.failures}",
                f"Big Five KPI: {scores or '—'}",
            )
        ),
        (
            "Батарея и scoring записаны",
            "Raw responses сохранены",
            "Model version явно связана для новых запусков",
        ),
        (
            "Открыть тесты",
            "Сравнить с другим портретом",
        ),
    )


def _portrait_claims(experiment, linked_version_id: str, versions) -> tuple[ResourceClaim, ...]:
    artifact = _linked_artifact(experiment)
    if not artifact and linked_version_id:
        linked = next(
            (
                item
                for item in versions
                if _value(item, "version_id") == linked_version_id
            ),
            None,
        )
        artifact = _value(linked, "artifact_path")
    return _claims(
        ("experiment", _value(experiment, "experiment_id")),
        ("model_version", linked_version_id),
        ("artifact_path", artifact),
    )


def _linked_version_id(experiment) -> str:
    match = _MODEL_VERSION_RE.search(_value(experiment, "subtitle"))
    return match.group(1).strip() if match else ""


def _linked_artifact(experiment) -> str:
    match = _ARTIFACT_RE.search(_value(experiment, "subtitle"))
    if match is None:
        return ""
    value = match.group(1).strip()
    return "" if value == "—" else value


def _training_tone(run) -> str:
    status = _value(run, "status").casefold()
    if "ошиб" in status or _value(run, "error_message"):
        return "bad"
    if "выполня" in status or "готов" in status:
        return "pending"
    if _value(run, "artifact_path"):
        return "good"
    return "neutral"


def _version_tone(version) -> str:
    status = _value(version, "status").casefold()
    if "ошиб" in status or "неуда" in status:
        return "bad"
    if _value(version, "artifact_path"):
        return "good"
    return "pending"


def _portrait_tone(view_model, experiment) -> str:
    stats = view_model._portrait_stats(experiment)  # noqa: SLF001
    if stats.failures:
        return "bad"
    if stats.total and stats.passed == stats.total:
        return "good"
    return "pending"


def _claims(*items: tuple[str, object]) -> tuple[ResourceClaim, ...]:
    unique: dict[tuple[str, str], ResourceClaim] = {}
    for kind, raw_id in items:
        identifier = str(raw_id or "").strip()
        if not identifier:
            continue
        claim = ResourceClaim(kind, identifier, "read")
        unique[claim.key] = claim
    return tuple(sorted(unique.values()))


def _value(item, name: str) -> str:
    if item is None:
        return ""
    return str(getattr(item, name, "") or "").strip()


def _stable_id(value: str) -> str:
    return sha1(value.encode("utf-8", errors="replace")).hexdigest()[:10]

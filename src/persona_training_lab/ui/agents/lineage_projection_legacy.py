from __future__ import annotations

from hashlib import sha1
import re

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.application.model_versions.status_mapping import (
    normalize_model_version_status,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.application.training.status_mapping import (
    normalize_training_status,
)
from persona_training_lab.domain.models.statuses import ModelVersionStatus
from persona_training_lab.domain.training.statuses import TrainingRunStatus
from persona_training_lab.ui.agents.lineage_presentation import (
    LineagePresentationProjection,
    ProjectedVersionNode,
)
from persona_training_lab.ui.viewmodels.agents import AgentDetailView
from persona_training_lab.ui.viewmodels.agents_legacy_semantics import (
    MISSING,
    messages,
    portrait_status_message,
    training_status_message,
    version_status_message,
)


_MODEL_VERSION_RE = re.compile(r"\bmodel_version=([^\s·]+)")
_ARTIFACT_RE = re.compile(r"\bartifact=([^\n·]+)")


def build_legacy_lineage(view_model) -> LineagePresentationProjection:
    """Project legacy service reads into the current presentation contract."""

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

    for run_index, run in enumerate(runs):
        run_id = _value(run, "run_id")
        if not run_id:
            continue
        base_model = _value(run, "base_model")
        dataset_title = _value(run, "dataset_version")
        base_key = base_model or "<unspecified>"
        dataset_key_value = dataset_title or "<unspecified>"
        base_label = base_model or UserMessage("agents.legacy.value.unspecified")
        dataset_label = dataset_title or UserMessage(
            "agents.legacy.value.unspecified"
        )
        base_node_id = base_nodes.get(base_key)
        if base_node_id is None:
            base_node_id = f"base:{_stable_id(base_key)}"
            base_nodes[base_key] = base_node_id
            nodes.append(
                ProjectedVersionNode(
                    base_node_id,
                    0,
                    UserMessage(
                        "agents.node.title.base_model",
                        {"label": base_label},
                    ),
                    UserMessage("agents.legacy.history.base.subtitle"),
                    UserMessage("agents.status.source"),
                    "neutral",
                    "side",
                    None,
                )
            )
            details[base_node_id] = AgentDetailView(
                UserMessage("agents.node.kind.base_model"),
                UserMessage(
                    "agents.legacy.history.base.body",
                    {"model": base_label},
                ),
                messages(
                    "agents.legacy.history.base.check.files",
                    "agents.legacy.history.base.check.protocol",
                ),
                messages("agents.legacy.history.base.action.source"),
            )
            resources[base_node_id] = _claims(("model_definition", base_model))
            context[base_node_id] = {
                "node_kind": "base_model",
                "base_model": base_model,
            }

        dataset_key = (base_key, dataset_key_value)
        dataset_node_id = dataset_nodes.get(dataset_key)
        if dataset_node_id is None:
            dataset_node_id = f"dataset:{_stable_id(base_key + '|' + dataset_key_value)}"
            dataset_nodes[dataset_key] = dataset_node_id
            nodes.append(
                ProjectedVersionNode(
                    dataset_node_id,
                    1,
                    UserMessage(
                        "agents.node.title.dataset",
                        {"label": dataset_label},
                    ),
                    UserMessage("agents.legacy.history.dataset.subtitle"),
                    UserMessage("agents.legacy.status.recorded"),
                    "neutral",
                    "side",
                    base_node_id,
                )
            )
            details[dataset_node_id] = AgentDetailView(
                UserMessage("agents.node.kind.dataset"),
                UserMessage(
                    "agents.legacy.history.dataset.body",
                    {
                        "dataset": dataset_label,
                        "model": base_label,
                    },
                ),
                messages(
                    "agents.legacy.history.dataset.check.recorded",
                    "agents.legacy.history.dataset.check.separate",
                ),
                messages("agents.legacy.history.dataset.action.dependency"),
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
                UserMessage(
                    "agents.node.title.training_run",
                    {"label": run_id},
                ),
                _training_subtitle(run),
                training_status_message(run),
                _training_tone(run),
                "side",
                dataset_node_id,
            )
        )
        details[node_id] = _training_detail(run)
        resources[node_id] = _training_claims(run)
        context[node_id] = _training_context(run)

    for version_index, version in enumerate(versions):
        version_id = _value(version, "version_id")
        if not version_id:
            continue
        node_id = "snapshot" if version_id == latest_version_id else f"version:{version_id}"
        version_nodes[version_id] = node_id
        training_run_id = _value(version, "training_run_id")
        parent_id = run_nodes.get(
            training_run_id,
            "training" if latest_run_id else "base",
        )
        if node_id != "snapshot":
            nodes.append(
                ProjectedVersionNode(
                    node_id,
                    3 + version_index,
                    UserMessage(
                        "agents.node.title.model_version",
                        {"label": version_id},
                    ),
                    _version_subtitle(version),
                    version_status_message(version),
                    _version_tone(version),
                    "side",
                    parent_id,
                )
            )
        details[node_id] = _version_detail(version)
        resources[node_id] = _version_claims(version)
        context[node_id] = _version_context(version)

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
                    UserMessage(
                        "agents.node.title.evaluation_run",
                        {
                            "label": (
                                _value(experiment, "title")
                                or experiment_id
                            )
                        },
                    ),
                    _portrait_subtitle(view_model, experiment),
                    portrait_status_message(experiment),
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

    for node_id in (
        "base",
        "dataset",
        "training",
        "snapshot",
        "portrait",
        "delta",
    ):
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
    return LineagePresentationProjection(
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
        *(("experiment", _value(item, "experiment_id")) for item in experiments[:2])
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


def _training_subtitle(run) -> UserMessage:
    artifact: object = _value(run, "artifact_path") or UserMessage(
        "agents.legacy.value.artifact_missing"
    )
    return UserMessage(
        "agents.legacy.history.training.subtitle",
        {
            "title": _value(run, "title") or MISSING,
            "progress": _value(run, "progress") or "0",
            "epoch": _value(run, "epoch_progress") or MISSING,
            "loss": _value(run, "loss") or MISSING,
            "artifact": artifact,
        },
    )


def _training_detail(run) -> AgentDetailView:
    return AgentDetailView(
        UserMessage("agents.node.kind.training_run"),
        UserMessage(
            "agents.legacy.history.training.body",
            {
                "run": _value(run, "run_id") or MISSING,
                "title": _value(run, "title") or MISSING,
                "status": training_status_message(run),
                "model": _value(run, "base_model") or MISSING,
                "profile": _value(run, "profile") or MISSING,
                "dataset": _value(run, "dataset_version") or MISSING,
                "epoch": _value(run, "epoch_progress") or MISSING,
                "loss": _value(run, "loss") or MISSING,
                "artifact": _value(run, "artifact_path") or MISSING,
                "error": (
                    _value(run, "error_message")
                    or UserMessage("agents.legacy.value.none")
                ),
            },
        ),
        messages(
            "agents.legacy.history.training.check.runtime",
            "agents.legacy.history.training.check.artifact",
            "agents.legacy.history.training.check.logs",
        ),
        messages(
            "agents.legacy.history.training.action.logs",
            "agents.legacy.history.training.action.snapshot",
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


def _version_subtitle(version) -> UserMessage:
    return UserMessage(
        "agents.legacy.history.version.subtitle",
        {
            "title": _value(version, "title") or MISSING,
            "run": _value(version, "training_run_id") or MISSING,
            "artifact": _value(version, "artifact_path") or MISSING,
        },
    )


def _version_detail(version) -> AgentDetailView:
    return AgentDetailView(
        UserMessage("agents.node.kind.model_version"),
        UserMessage(
            "agents.legacy.history.version.body",
            {
                "version": _value(version, "version_id") or MISSING,
                "title": _value(version, "title") or MISSING,
                "status": version_status_message(version),
                "run": _value(version, "training_run_id") or MISSING,
                "model": _value(version, "base_model") or MISSING,
                "profile": _value(version, "profile_title") or MISSING,
                "dataset": _value(version, "dataset_title") or MISSING,
                "artifact": _value(version, "artifact_path") or MISSING,
                "quality": _value(version, "quality_summary") or MISSING,
            },
        ),
        messages(
            "agents.legacy.history.version.check.registered",
            "agents.legacy.history.version.check.artifact",
            "agents.legacy.history.version.check.run",
        ),
        messages(
            "agents.legacy.history.version.action.compare",
            "agents.legacy.history.version.action.portrait",
            "agents.legacy.history.version.action.branch",
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


def _portrait_subtitle(view_model, experiment) -> UserMessage:
    stats = view_model._portrait_stats(experiment)  # noqa: SLF001
    scores = view_model._score_line(stats.scores)  # noqa: SLF001
    return UserMessage(
        "agents.legacy.history.portrait.subtitle",
        {
            "passed": stats.passed,
            "total": stats.total,
            "failures": stats.failures,
            "scores": (
                scores
                if scores
                else UserMessage("agents.legacy.value.no_kpi")
            ),
        },
    )


def _portrait_detail(view_model, experiment) -> AgentDetailView:
    stats = view_model._portrait_stats(experiment)  # noqa: SLF001
    scores = view_model._score_line(stats.scores)  # noqa: SLF001
    linked_version = _linked_version_id(experiment)
    return AgentDetailView(
        UserMessage("agents.legacy.kind.portrait"),
        UserMessage(
            "agents.legacy.history.portrait.body",
            {
                "experiment": _value(experiment, "experiment_id") or MISSING,
                "title": _value(experiment, "title") or MISSING,
                "status": portrait_status_message(experiment),
                "version": (
                    linked_version
                    or UserMessage("agents.legacy.value.legacy_unspecified")
                ),
                "passed": stats.passed,
                "total": stats.total,
                "failures": stats.failures,
                "scores": scores or MISSING,
            },
        ),
        messages(
            "agents.legacy.history.portrait.check.protocol",
            "agents.legacy.history.portrait.check.raw",
            "agents.legacy.history.portrait.check.version",
        ),
        messages(
            "agents.legacy.history.portrait.action.tests",
            "agents.legacy.history.portrait.action.compare",
        ),
    )


def _portrait_claims(
    experiment,
    linked_version_id: str,
    versions,
) -> tuple[ResourceClaim, ...]:
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
    return "" if value == MISSING else value


def _training_tone(run) -> str:
    status = normalize_training_status(_value(run, "status"))
    if status is TrainingRunStatus.FAILED or _value(run, "error_message"):
        return "bad"
    if status in {
        TrainingRunStatus.CREATED,
        TrainingRunStatus.READY,
        TrainingRunStatus.RUNNING,
    }:
        return "pending"
    if status is TrainingRunStatus.COMPLETED or _value(run, "artifact_path"):
        return "good"
    return "neutral"


def _version_tone(version) -> str:
    status = normalize_model_version_status(_value(version, "status"))
    if status is ModelVersionStatus.FAILED:
        return "bad"
    if status is ModelVersionStatus.READY or _value(version, "artifact_path"):
        return "good"
    if status in {ModelVersionStatus.DRAFT, ModelVersionStatus.ARCHIVED}:
        return "pending"
    return "neutral"


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


__all__ = ("build_legacy_lineage",)

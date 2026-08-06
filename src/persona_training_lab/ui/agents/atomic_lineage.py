from __future__ import annotations

from collections.abc import Iterable

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageSnapshot,
)
from persona_training_lab.application.lineage.projection import (
    LineageEdge,
    LineageEntityKind,
    LineageNode,
    LineageProjection,
    LineageRelation,
    LineageState,
)
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.real_lineage import (
    ProjectedVersionNode,
    RealLineageProjection,
    build_real_lineage as build_legacy_lineage,
)
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


_CANONICAL_BY_KIND = {
    LineageEntityKind.BASE_MODEL: "base",
    LineageEntityKind.DATASET: "dataset",
    LineageEntityKind.TRAINING_RUN: "training",
    LineageEntityKind.MODEL_VERSION: "snapshot",
    LineageEntityKind.EVALUATION_RUN: "portrait",
}
_PREFIX_BY_KIND = {
    LineageEntityKind.BASE_MODEL: "Base",
    LineageEntityKind.PERSONA_PROFILE: "Profile",
    LineageEntityKind.DATASET: "Dataset",
    LineageEntityKind.TRAINING_RUN: "Train",
    LineageEntityKind.ARTIFACT: "Artifact",
    LineageEntityKind.MODEL_VERSION: "Version",
    LineageEntityKind.EVALUATION_RUN: "Portrait",
}
_PRIMARY_RELATION_PRIORITY = {
    LineageRelation.BACKS_VERSION: 0,
    LineageRelation.PRODUCES_VERSION: 1,
    LineageRelation.EVALUATES_VERSION: 2,
    LineageRelation.PRODUCES_ARTIFACT: 3,
    LineageRelation.USES_DATASET: 4,
    LineageRelation.USES_BASE_MODEL: 5,
    LineageRelation.USES_PROFILE: 6,
    LineageRelation.SUPPLIES_EVALUATION: 7,
}


def build_real_lineage(view_model) -> RealLineageProjection:
    snapshot_builder = getattr(view_model, "build_lineage_snapshot", None)
    if not callable(snapshot_builder):
        return build_legacy_lineage(view_model)
    return _build_canvas_projection(snapshot_builder())


def _build_canvas_projection(
    atomic: AtomicLineageSnapshot,
) -> RealLineageProjection:
    projection = atomic.projection
    aliases = _canonical_aliases(atomic)
    display_id = {
        node.node_id: aliases.get(node.node_id, node.node_id)
        for node in projection.nodes
    }
    primary_parent = _primary_parents(projection)

    nodes: list[ProjectedVersionNode] = []
    details: dict[str, AgentDetailView] = {}
    resources: dict[str, tuple[ResourceClaim, ...]] = {}
    context: dict[str, dict[str, str]] = {}

    for node in projection.nodes:
        node_id = display_id[node.node_id]
        parent_semantic = primary_parent.get(node.node_id)
        parent_id = (
            display_id.get(parent_semantic, parent_semantic)
            if parent_semantic
            else None
        )
        is_canonical = node_id in _CANONICAL_BY_KIND.values()
        nodes.append(
            ProjectedVersionNode(
                node_id=node_id,
                depth=_depth(node.node_id, primary_parent),
                title=_title(node),
                subtitle=_subtitle(node, projection),
                status=node.state.value,
                tone=_tone(node.state),
                branch_note=(
                    "current"
                    if node_id == "snapshot"
                    else "main" if is_canonical else "side"
                ),
                parent_id=parent_id,
            )
        )
        details[node_id] = _detail(node, projection)
        resources[node_id] = node.claims
        context[node_id] = _context(node)

    _ensure_placeholders(nodes, details, resources, context)
    _append_delta(nodes, details, resources, context, atomic)
    nodes.sort(key=lambda item: (item.depth, item.node_id))

    return RealLineageProjection(
        nodes=tuple(nodes),
        details=details,
        resources=resources,
        entity_context=context,
        signature=(
            (
                "atomic-lineage",
                projection.topology_revision,
                projection.content_revision,
                _presentation_signature(aliases, atomic),
            ),
        ),
    )


def _canonical_aliases(
    atomic: AtomicLineageSnapshot,
) -> dict[str, str]:
    source = atomic.source
    projection = atomic.projection
    aliases: dict[str, str] = {}

    latest_run = _latest(source.training_runs, "run_id")
    latest_version = _latest(source.model_versions, "version_id")
    latest_evaluation = _latest(source.evaluations, "experiment_id")

    run_node_id = _node_id_for_entity(
        projection,
        LineageEntityKind.TRAINING_RUN,
        getattr(latest_run, "run_id", ""),
    )
    version_node_id = _node_id_for_entity(
        projection,
        LineageEntityKind.MODEL_VERSION,
        getattr(latest_version, "version_id", ""),
    )
    evaluation_node_id = _node_id_for_entity(
        projection,
        LineageEntityKind.EVALUATION_RUN,
        getattr(latest_evaluation, "experiment_id", ""),
    )
    if run_node_id:
        aliases[run_node_id] = "training"
        for edge in projection.incoming(run_node_id):
            source_node = projection.node(edge.source_node_id)
            if source_node is None:
                continue
            alias = _CANONICAL_BY_KIND.get(source_node.kind)
            if alias in {"base", "dataset"}:
                aliases[source_node.node_id] = alias
    if version_node_id:
        aliases[version_node_id] = "snapshot"
    if evaluation_node_id:
        aliases[evaluation_node_id] = "portrait"
    return aliases


def _presentation_signature(
    aliases: dict[str, str],
    atomic: AtomicLineageSnapshot,
) -> str:
    alias_items = [
        f"{semantic_id}->{display_id}"
        for semantic_id, display_id in sorted(aliases.items())
    ]
    evaluations = sorted(
        atomic.source.evaluations,
        key=lambda item: (item.updated_at, item.experiment_id),
        reverse=True,
    )[:2]
    alias_items.extend(
        f"delta:{index}={item.experiment_id}"
        for index, item in enumerate(evaluations)
    )
    return "|".join(alias_items)


def _latest(records: Iterable[object], id_field: str) -> object | None:
    values = tuple(records)
    if not values:
        return None
    return max(
        values,
        key=lambda item: (
            str(getattr(item, "updated_at", "") or ""),
            str(getattr(item, id_field, "") or ""),
        ),
    )


def _node_id_for_entity(
    projection: LineageProjection,
    kind: LineageEntityKind,
    entity_id: str,
) -> str:
    if not entity_id:
        return ""
    for node in projection.nodes:
        if node.kind is kind and node.entity_id == entity_id:
            return node.node_id
    return ""


def _primary_parents(
    projection: LineageProjection,
) -> dict[str, str]:
    parents: dict[str, str] = {}
    incoming: dict[str, list[LineageEdge]] = {}
    for edge in projection.edges:
        incoming.setdefault(edge.target_node_id, []).append(edge)
    for target_id, edges in incoming.items():
        selected = min(
            edges,
            key=lambda edge: (
                _PRIMARY_RELATION_PRIORITY.get(edge.relation, 100),
                edge.source_node_id,
            ),
        )
        parents[target_id] = selected.source_node_id
    return parents


def _depth(
    node_id: str,
    parents: dict[str, str],
) -> int:
    seen: set[str] = set()
    current = node_id
    depth = 0
    while current in parents and current not in seen:
        seen.add(current)
        current = parents[current]
        depth += 1
    return depth


def _title(node: LineageNode) -> str:
    prefix = _PREFIX_BY_KIND[node.kind]
    label = (
        node.attributes.get("title")
        or node.attributes.get("path")
        or node.attributes.get("reference")
        or node.entity_id
    )
    return f"{prefix} · {label}"


def _subtitle(
    node: LineageNode,
    projection: LineageProjection,
) -> str:
    attributes = [
        f"{key}={value}"
        for key, value in sorted(node.attributes.items())
        if value and key not in {"title", "status"}
    ]
    unresolved = [
        item
        for item in projection.unresolved
        if item.dependent_node_id == node.node_id
    ]
    attributes.extend(
        f"unresolved:{item.relation.value}={item.reason_code}"
        for item in unresolved
    )
    return " · ".join(attributes) or node.kind.value


def _tone(state: LineageState) -> str:
    if state is LineageState.READY:
        return "good"
    if state is LineageState.FAILED:
        return "bad"
    if state in {
        LineageState.PENDING,
        LineageState.RUNNING,
        LineageState.PARTIAL,
    }:
        return "pending"
    return "neutral"


def _detail(
    node: LineageNode,
    projection: LineageProjection,
) -> AgentDetailView:
    body_lines = [
        f"kind: {node.kind.value}",
        f"entity: {node.entity_id}",
        f"state: {node.state.value}",
    ]
    body_lines.extend(
        f"{key}: {value}"
        for key, value in sorted(node.attributes.items())
        if value
    )
    unresolved = tuple(
        item
        for item in projection.unresolved
        if item.dependent_node_id == node.node_id
    )
    body_lines.extend(
        "unresolved "
        f"{item.relation.value}: {item.reference or '∅'} "
        f"({item.reason_code})"
        for item in unresolved
    )
    checks = tuple(
        f"{edge.relation.value}: {edge.source_node_id}"
        for edge in projection.incoming(node.node_id)
    ) or ("semantic node registered",)
    return AgentDetailView(
        title=node.kind.value,
        body="\n".join(body_lines),
        checks=checks,
        actions=(),
    )


def _context(node: LineageNode) -> dict[str, str]:
    context = {
        "node_kind": node.kind.value,
        "entity_id": node.entity_id,
        **dict(node.attributes),
    }
    id_key = {
        LineageEntityKind.DATASET: "dataset_id",
        LineageEntityKind.TRAINING_RUN: "training_run_id",
        LineageEntityKind.MODEL_VERSION: "model_version_id",
        LineageEntityKind.EVALUATION_RUN: "experiment_id",
        LineageEntityKind.ARTIFACT: "artifact_path",
        LineageEntityKind.BASE_MODEL: "base_model",
        LineageEntityKind.PERSONA_PROFILE: "profile_title",
    }[node.kind]
    context[id_key] = node.entity_id
    for claim in node.claims:
        context.setdefault(claim.resource_kind, claim.resource_id)
    return context


def _ensure_placeholders(
    nodes: list[ProjectedVersionNode],
    details: dict[str, AgentDetailView],
    resources: dict[str, tuple[ResourceClaim, ...]],
    context: dict[str, dict[str, str]],
) -> None:
    existing = {node.node_id for node in nodes}
    chain = (
        ("base", None, "Base"),
        ("dataset", "base", "Dataset"),
        ("training", "dataset", "Train"),
        ("snapshot", "training", "Version"),
        ("portrait", "snapshot", "Portrait"),
    )
    for depth, (node_id, parent_id, title) in enumerate(chain):
        if node_id in existing:
            continue
        nodes.append(
            ProjectedVersionNode(
                node_id=node_id,
                depth=depth,
                title=f"{title} · —",
                subtitle="presentation placeholder",
                status=LineageState.PENDING.value,
                tone="pending",
                branch_note=(
                    "current" if node_id == "snapshot" else "main"
                ),
                parent_id=parent_id,
            )
        )
        details[node_id] = AgentDetailView(
            title=title,
            body="No persisted semantic entity is linked to this stage.",
            checks=("awaiting persisted entity",),
            actions=(),
        )
        resources[node_id] = ()
        context[node_id] = {
            "node_kind": f"{node_id}_placeholder",
        }


def _append_delta(
    nodes: list[ProjectedVersionNode],
    details: dict[str, AgentDetailView],
    resources: dict[str, tuple[ResourceClaim, ...]],
    context: dict[str, dict[str, str]],
    atomic: AtomicLineageSnapshot,
) -> None:
    evaluations = sorted(
        atomic.source.evaluations,
        key=lambda item: (item.updated_at, item.experiment_id),
        reverse=True,
    )
    ready = len(evaluations) >= 2
    parent_id = "portrait" if evaluations else "snapshot"
    nodes.append(
        ProjectedVersionNode(
            node_id="delta",
            depth=5,
            title="Delta · latest - previous",
            subtitle=(
                "two exact evaluation runs available"
                if ready
                else "second evaluation run required"
            ),
            status=(
                LineageState.READY.value
                if ready
                else LineageState.PENDING.value
            ),
            tone="good" if ready else "pending",
            branch_note="main",
            parent_id=parent_id,
        )
    )
    selected = evaluations[:2]
    claims = tuple(
        ResourceClaim("experiment", item.experiment_id)
        for item in selected
    )
    resources["delta"] = claims
    context["delta"] = {
        "node_kind": "analysis_delta",
        "left_experiment_id": (
            selected[0].experiment_id if selected else ""
        ),
        "right_experiment_id": (
            selected[1].experiment_id if len(selected) > 1 else ""
        ),
    }
    details["delta"] = AgentDetailView(
        title="analysis_delta",
        body="\n".join(
            (
                f"left: {context['delta']['left_experiment_id'] or '—'}",
                f"right: {context['delta']['right_experiment_id'] or '—'}",
            )
        ),
        checks=(
            "two exact evaluation runs"
            if ready
            else "second exact evaluation run missing",
        ),
        actions=(),
    )

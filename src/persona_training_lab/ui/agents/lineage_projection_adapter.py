from __future__ import annotations

from collections.abc import Iterable

from persona_training_lab.application.experiments.protocol import (
    portrait_protocols_match,
)
from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageSnapshot,
)
from persona_training_lab.application.lineage.projection_builder import (
    build_lineage_projection,
)
from persona_training_lab.application.lineage.projection_model import (
    LineageEdge,
    LineageEntityKind,
    LineageNode,
    LineageProjection,
    LineageRelation,
    LineageState,
)
from persona_training_lab.application.lineage.snapshot import LineageSourceSnapshot
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.ui.agents.lineage_presentation import (
    LineagePresentationProjection,
    ProjectedVersionNode,
)
from persona_training_lab.ui.viewmodels.agents import AgentDetailView


_CANONICAL_BY_KIND = {
    LineageEntityKind.BASE_MODEL: "base",
    LineageEntityKind.DATASET: "dataset",
    LineageEntityKind.TRAINING_RUN: "training",
    LineageEntityKind.MODEL_VERSION: "snapshot",
    LineageEntityKind.EVALUATION_RUN: "portrait",
}
_KIND_ID_BY_KIND = {
    LineageEntityKind.BASE_MODEL: "base_model",
    LineageEntityKind.PERSONA_PROFILE: "persona_profile",
    LineageEntityKind.DATASET: "dataset",
    LineageEntityKind.TRAINING_RUN: "training_run",
    LineageEntityKind.ARTIFACT: "artifact",
    LineageEntityKind.MODEL_VERSION: "model_version",
    LineageEntityKind.EVALUATION_RUN: "evaluation_run",
}
_PRIMARY_RELATION_PRIORITY = {
    LineageRelation.PRODUCES_VERSION: 0,
    LineageRelation.BACKS_VERSION: 1,
    LineageRelation.EVALUATES_VERSION: 2,
    LineageRelation.PRODUCES_ARTIFACT: 3,
    LineageRelation.USES_DATASET: 4,
    LineageRelation.USES_BASE_MODEL: 5,
    LineageRelation.USES_PROFILE: 6,
    LineageRelation.SUPPLIES_EVALUATION: 7,
}


def build_atomic_lineage(
    atomic: AtomicLineageSnapshot,
) -> LineagePresentationProjection:
    """Project one immutable semantic snapshot into the Agents workspace."""

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
        claims = _dependency_claims(node.node_id, projection)
        nodes.append(
            ProjectedVersionNode(
                node_id=node_id,
                depth=_depth(node.node_id, primary_parent),
                title=_title(node),
                subtitle=_subtitle(node, projection),
                status=_state_message(node.state),
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
        resources[node_id] = claims
        context[node_id] = _context(node, claims)

    _ensure_placeholders(nodes, details, resources, context)
    _append_delta(nodes, details, resources, context, atomic)
    nodes.sort(key=lambda item: (item.depth, item.node_id))

    return LineagePresentationProjection(
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


def build_empty_lineage() -> LineagePresentationProjection:
    """Create explicit presentation placeholders without touching persistence."""

    return build_atomic_lineage(
        AtomicLineageSnapshot(
            source=LineageSourceSnapshot(),
            projection=build_lineage_projection(),
        )
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


def _title(node: LineageNode) -> UserMessage:
    label = (
        node.attributes.get("title")
        or node.attributes.get("path")
        or node.attributes.get("reference")
        or node.entity_id
    )
    kind_id = _KIND_ID_BY_KIND[node.kind]
    return UserMessage(
        f"agents.node.title.{kind_id}",
        {"label": label},
    )


def _subtitle(
    node: LineageNode,
    projection: LineageProjection,
) -> UserMessage:
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
        f"{item.relation.value}={item.reason_code}"
        for item in unresolved
    )
    if attributes:
        return UserMessage(
            "agents.node.subtitle.attributes",
            {"attributes": " · ".join(attributes)},
        )
    return UserMessage(
        f"agents.node.kind.{_KIND_ID_BY_KIND[node.kind]}"
    )


def _state_message(state: LineageState) -> UserMessage:
    return UserMessage(f"agents.lineage_state.{state.value}")


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
    attributes = "\n".join(
        f"{key}: {value}"
        for key, value in sorted(node.attributes.items())
        if value
    )
    unresolved = tuple(
        item
        for item in projection.unresolved
        if item.dependent_node_id == node.node_id
    )
    unresolved_text = "\n".join(
        f"{item.relation.value}: {item.reference or '∅'} ({item.reason_code})"
        for item in unresolved
    )
    checks = tuple(
        UserMessage(
            "agents.detail.relation_check",
            {
                "relation": edge.relation.value,
                "source": edge.source_node_id,
            },
        )
        for edge in projection.incoming(node.node_id)
    ) or (UserMessage("agents.detail.semantic_node_registered"),)
    return AgentDetailView(
        title=UserMessage(
            f"agents.node.kind.{_KIND_ID_BY_KIND[node.kind]}"
        ),
        body=UserMessage(
            "agents.detail.semantic_body",
            {
                "kind": node.kind.value,
                "entity": node.entity_id,
                "state": node.state.value,
                "attributes": attributes or "—",
                "unresolved": unresolved_text or "—",
            },
        ),
        checks=checks,
        actions=(),
    )


def _dependency_claims(
    node_id: str,
    projection: LineageProjection,
) -> tuple[ResourceClaim, ...]:
    by_id = {node.node_id: node for node in projection.nodes}
    incoming: dict[str, tuple[str, ...]] = {}
    for node in projection.nodes:
        incoming[node.node_id] = tuple(
            edge.source_node_id
            for edge in projection.incoming(node.node_id)
        )

    claims: set[ResourceClaim] = set()
    pending = [node_id]
    visited: set[str] = set()
    while pending:
        current_id = pending.pop()
        if current_id in visited:
            continue
        visited.add(current_id)
        current = by_id.get(current_id)
        if current is None:
            continue
        claims.update(current.claims)
        pending.extend(incoming.get(current_id, ()))
    return tuple(sorted(claims))


def _context(
    node: LineageNode,
    claims: tuple[ResourceClaim, ...],
) -> dict[str, str]:
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
    for claim in claims:
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
        ("base", None, "base_model"),
        ("dataset", "base", "dataset"),
        ("training", "dataset", "training_run"),
        ("snapshot", "training", "model_version"),
        ("portrait", "snapshot", "evaluation_run"),
    )
    for depth, (node_id, parent_id, kind_id) in enumerate(chain):
        if node_id in existing:
            continue
        nodes.append(
            ProjectedVersionNode(
                node_id=node_id,
                depth=depth,
                title=UserMessage(
                    f"agents.node.placeholder_title.{kind_id}"
                ),
                subtitle=UserMessage("agents.node.placeholder.subtitle"),
                status=_state_message(LineageState.PENDING),
                tone="pending",
                branch_note=(
                    "current" if node_id == "snapshot" else "main"
                ),
                parent_id=parent_id,
            )
        )
        details[node_id] = AgentDetailView(
            title=UserMessage(f"agents.node.kind.{kind_id}"),
            body=UserMessage("agents.detail.placeholder.body"),
            checks=(UserMessage("agents.detail.placeholder.check"),),
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
    selected = evaluations[:2]
    has_pair = len(selected) >= 2
    ready = bool(
        has_pair
        and portrait_protocols_match(
            selected[0].subtitle,
            selected[1].subtitle,
        )
    )
    parent_id = "portrait" if evaluations else "snapshot"
    nodes.append(
        ProjectedVersionNode(
            node_id="delta",
            depth=5,
            title=UserMessage("agents.node.delta.title"),
            subtitle=UserMessage(
                "agents.node.delta.subtitle.ready"
                if ready
                else (
                    "agents.next.delta"
                    if has_pair
                    else "agents.node.delta.subtitle.pending"
                )
            ),
            status=_state_message(
                LineageState.READY if ready else LineageState.PENDING
            ),
            tone="good" if ready else "pending",
            branch_note="main",
            parent_id=parent_id,
        )
    )
    claims = tuple(
        ResourceClaim("experiment", item.experiment_id)
        for item in selected
    )
    resources["delta"] = claims
    candidate_left = selected[0].experiment_id if selected else ""
    candidate_right = (
        selected[1].experiment_id if len(selected) > 1 else ""
    )
    context["delta"] = {
        "node_kind": "analysis_delta",
        "left_experiment_id": candidate_left if ready else "",
        "right_experiment_id": candidate_right if ready else "",
        "candidate_left_experiment_id": candidate_left,
        "candidate_right_experiment_id": candidate_right,
        "comparison_reason": (
            ""
            if ready
            else "protocol_mismatch" if has_pair else "missing_second_evaluation"
        ),
    }
    details["delta"] = AgentDetailView(
        title=UserMessage("agents.node.kind.analysis_delta"),
        body=UserMessage(
            "agents.detail.delta.body",
            {
                "left": candidate_left or "—",
                "right": candidate_right or "—",
            },
        ),
        checks=(
            UserMessage(
                "agents.detail.delta.check.ready"
                if ready
                else (
                    "agents.next.delta"
                    if has_pair
                    else "agents.detail.delta.check.pending"
                )
            ),
        ),
        actions=(),
    )


__all__ = ("build_atomic_lineage", "build_empty_lineage")

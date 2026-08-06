from persona_training_lab.ui.agents.projection_updates import (
    ProjectionUpdateKind,
    ProjectionUpdatePlanner,
)
from persona_training_lab.ui.agents.refresh_worker import LineageRevisionSet


def _revisions(
    topology: str = "topology-1",
    content: str = "content-1",
    presentation: str = "presentation-1",
) -> LineageRevisionSet:
    return LineageRevisionSet(
        topology=topology,
        content=content,
        presentation=presentation,
    )


def test_first_projection_requires_full_update() -> None:
    planner = ProjectionUpdatePlanner()

    assert planner.plan(_revisions()) is ProjectionUpdateKind.FULL


def test_identical_revision_is_noop_after_commit() -> None:
    planner = ProjectionUpdatePlanner()
    revisions = _revisions()
    planner.commit(revisions)

    assert planner.plan(revisions) is ProjectionUpdateKind.NOOP


def test_content_only_change_uses_fast_repaint() -> None:
    planner = ProjectionUpdatePlanner()
    planner.commit(_revisions())

    assert planner.plan(
        _revisions(content="content-2")
    ) is ProjectionUpdateKind.CONTENT


def test_topology_or_presentation_change_requires_full_update() -> None:
    planner = ProjectionUpdatePlanner()
    planner.commit(_revisions())

    assert planner.plan(
        _revisions(topology="topology-2")
    ) is ProjectionUpdateKind.FULL
    assert planner.plan(
        _revisions(presentation="presentation-2")
    ) is ProjectionUpdateKind.FULL

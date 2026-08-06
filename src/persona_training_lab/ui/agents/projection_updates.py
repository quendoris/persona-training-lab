from __future__ import annotations

from enum import Enum

from persona_training_lab.ui.agents.refresh_worker import LineageRevisionSet


class ProjectionUpdateKind(str, Enum):
    NOOP = "noop"
    CONTENT = "content"
    FULL = "full"


class ProjectionUpdatePlanner:
    """Classify immutable lineage revisions without depending on QWidget."""

    def __init__(self) -> None:
        self._current: LineageRevisionSet | None = None

    @property
    def current(self) -> LineageRevisionSet | None:
        return self._current

    def plan(self, incoming: LineageRevisionSet) -> ProjectionUpdateKind:
        current = self._current
        if current == incoming:
            return ProjectionUpdateKind.NOOP
        if (
            current is None
            or current.topology != incoming.topology
            or current.presentation != incoming.presentation
        ):
            return ProjectionUpdateKind.FULL
        return ProjectionUpdateKind.CONTENT

    def commit(self, applied: LineageRevisionSet) -> None:
        self._current = applied

from __future__ import annotations

import traceback
from dataclasses import dataclass
from types import MappingProxyType

from PySide6.QtCore import QObject, QThread, Signal, Slot

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageSnapshot,
)
from persona_training_lab.application.lineage.loader import LineageLoaderFactory
from persona_training_lab.ui.agents.lineage_presentation import (
    LineagePresentationProjection,
)
from persona_training_lab.ui.agents.lineage_projection_adapter import (
    build_atomic_lineage,
)


@dataclass(frozen=True, slots=True)
class LineageRevisionSet:
    topology: str
    content: str
    presentation: str


@dataclass(frozen=True, slots=True)
class LineageRefreshResult:
    generation: int
    atomic: AtomicLineageSnapshot
    projection: LineagePresentationProjection
    revisions: LineageRevisionSet


@dataclass(frozen=True, slots=True)
class LineageRefreshFailure:
    generation: int
    error_type: str
    message: str
    traceback_text: str


class LineageRefreshWorker(QObject):
    completed = Signal(object)
    failed = Signal(object)

    def __init__(self, loader_factory: LineageLoaderFactory) -> None:
        super().__init__()
        self._loader_factory = loader_factory
        self._loader = None
        self._closed = False

    @Slot(int)
    def refresh(self, generation: int) -> None:
        if self._closed:
            return
        try:
            loader = self._loader
            if loader is None:
                loader = self._loader_factory()
                self._loader = loader
            atomic = loader.build_snapshot()
            projection = _freeze_projection(build_atomic_lineage(atomic))
            self.completed.emit(
                LineageRefreshResult(
                    generation=generation,
                    atomic=atomic,
                    projection=projection,
                    revisions=LineageRevisionSet(
                        topology=atomic.projection.topology_revision,
                        content=atomic.projection.content_revision,
                        presentation=_presentation_revision(projection),
                    ),
                )
            )
        except Exception as error:
            self._discard_loader()
            self.failed.emit(
                LineageRefreshFailure(
                    generation=generation,
                    error_type=type(error).__name__,
                    message=str(error),
                    traceback_text=traceback.format_exc(limit=20),
                )
            )

    @Slot()
    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._discard_loader()
        QThread.currentThread().quit()

    def _discard_loader(self) -> None:
        loader = self._loader
        self._loader = None
        if loader is None:
            return
        try:
            loader.close()
        except Exception:
            # Recovery and shutdown must continue even if a provider-specific
            # close hook fails. The original refresh error remains primary.
            pass


def _freeze_projection(
    projection: LineagePresentationProjection,
) -> LineagePresentationProjection:
    contexts = {
        node_id: MappingProxyType(dict(values))
        for node_id, values in projection.entity_context.items()
    }
    return LineagePresentationProjection(
        nodes=tuple(projection.nodes),
        details=MappingProxyType(dict(projection.details)),
        resources=MappingProxyType(dict(projection.resources)),
        entity_context=MappingProxyType(contexts),
        signature=tuple(projection.signature),
    )


def _presentation_revision(projection: LineagePresentationProjection) -> str:
    if not projection.signature:
        return ""
    head = projection.signature[0]
    return head[3] if len(head) > 3 else ""

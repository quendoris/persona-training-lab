from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageSnapshot,
)


class AtomicLineageLoader(Protocol):
    """Worker-owned loader for one atomic lineage projection snapshot."""

    def build_snapshot(self) -> AtomicLineageSnapshot: ...

    def close(self) -> None: ...


LineageLoaderFactory = Callable[[], AtomicLineageLoader]

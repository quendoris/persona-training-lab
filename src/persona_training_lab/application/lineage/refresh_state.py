from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RefreshDecision:
    accepted: bool
    dispatch_generation: int | None
    interval_ms: int


@dataclass(slots=True)
class LineageRefreshSchedule:
    """Coalesce refreshes, reject stale results and apply bounded backoff."""

    base_interval_ms: int = 1_200
    max_interval_ms: int = 30_000
    generation: int = 0
    active_generation: int = 0
    busy: bool = False
    pending: bool = False
    pending_force: bool = False
    consecutive_failures: int = 0
    stopped: bool = False
    interval_ms: int = field(init=False)

    def __post_init__(self) -> None:
        if self.base_interval_ms <= 0:
            raise ValueError("base_interval_ms must be positive")
        if self.max_interval_ms < self.base_interval_ms:
            raise ValueError(
                "max_interval_ms must be greater than or equal to base_interval_ms"
            )
        self.interval_ms = self.base_interval_ms

    def request(self, *, force: bool = False) -> int | None:
        if self.stopped:
            return None
        if self.busy:
            self.pending = True
            self.pending_force = self.pending_force or force
            return None
        return self._dispatch()

    def complete_success(self, generation: int) -> RefreshDecision:
        if not self._accepts(generation):
            return RefreshDecision(False, None, self.interval_ms)
        self.busy = False
        self.active_generation = 0
        self.consecutive_failures = 0
        self.interval_ms = self.base_interval_ms
        dispatch = None
        if self.pending:
            self.pending = False
            self.pending_force = False
            dispatch = self._dispatch()
        return RefreshDecision(True, dispatch, self.interval_ms)

    def complete_failure(self, generation: int) -> RefreshDecision:
        if not self._accepts(generation):
            return RefreshDecision(False, None, self.interval_ms)
        self.busy = False
        self.active_generation = 0
        self.consecutive_failures += 1
        multiplier = 2 ** min(self.consecutive_failures, 10)
        self.interval_ms = min(
            self.max_interval_ms,
            self.base_interval_ms * multiplier,
        )
        dispatch = None
        if self.pending_force:
            self.pending = False
            self.pending_force = False
            dispatch = self._dispatch()
        else:
            self.pending = False
            self.pending_force = False
        return RefreshDecision(True, dispatch, self.interval_ms)

    def stop(self) -> None:
        self.stopped = True
        self.pending = False
        self.pending_force = False

    def _dispatch(self) -> int:
        self.generation += 1
        self.active_generation = self.generation
        self.busy = True
        return self.active_generation

    def _accepts(self, generation: int) -> bool:
        return (
            not self.stopped
            and self.busy
            and generation == self.active_generation
        )

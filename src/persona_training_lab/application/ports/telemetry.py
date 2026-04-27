from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class ProcessMetrics:
    pid: int
    name: str
    cpu_percent: float
    ram_percent: float


@dataclass(slots=True, frozen=True)
class BaseTelemetryMetrics:
    cpu_percent: float
    cpu_logical_cores: int
    ram_used_bytes: int
    ram_total_bytes: int
    ram_percent: float
    processes: tuple[ProcessMetrics, ...]


@dataclass(slots=True, frozen=True)
class GpuTelemetryMetrics:
    gpu_util_percent: float
    vram_used_mb: float
    vram_total_mb: float
    temperature_c: float | None


class SystemMetricsProviderPort(Protocol):
    def collect_base_metrics(self) -> BaseTelemetryMetrics: ...


class GpuMetricsProviderPort(Protocol):
    def collect_gpu_metrics(self) -> GpuTelemetryMetrics: ...

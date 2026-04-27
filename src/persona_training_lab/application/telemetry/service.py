from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from persona_training_lab.application.ports.telemetry import (
    BaseTelemetryMetrics,
    GpuMetricsProviderPort,
    SystemMetricsProviderPort,
)


@dataclass(slots=True, frozen=True)
class TelemetryProcessRow:
    pid: int
    name: str
    cpu_percent: float
    ram_percent: float


@dataclass(slots=True, frozen=True)
class TelemetrySnapshot:
    cpu_percent: float
    cpu_logical_cores: int
    cpu_status: str
    ram_used_bytes: int
    ram_total_bytes: int
    ram_percent: float
    gpu_status: str
    gpu_util_percent: float | None
    vram_used_mb: float | None
    vram_total_mb: float | None
    gpu_temperature_c: float | None
    processes: tuple[TelemetryProcessRow, ...]
    processes_status: str
    status: str
    last_updated_at: str
    error_message: str


@dataclass(slots=True)
class SystemTelemetryService:
    system_provider: SystemMetricsProviderPort
    gpu_provider: GpuMetricsProviderPort | None = None

    def collect_snapshot(self) -> TelemetrySnapshot:
        base: BaseTelemetryMetrics
        try:
            base = self.system_provider.collect_base_metrics()
        except Exception:
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            return TelemetrySnapshot(
                cpu_percent=0.0,
                cpu_logical_cores=0,
                cpu_status="Норма",
                ram_used_bytes=0,
                ram_total_bytes=0,
                ram_percent=0.0,
                gpu_status="Источник GPU не подключён",
                gpu_util_percent=None,
                vram_used_mb=None,
                vram_total_mb=None,
                gpu_temperature_c=None,
                processes=(),
                processes_status="Данные процессов пока недоступны",
                status="Телеметрия активна",
                last_updated_at=now,
                error_message="Не удалось обновить телеметрию",
            )

        gpu_status = "Источник GPU не подключён"
        gpu_util: float | None = None
        vram_used: float | None = None
        vram_total: float | None = None
        gpu_temp: float | None = None
        error_message = ""

        if self.gpu_provider is not None:
            try:
                gpu = self.gpu_provider.collect_gpu_metrics()
                gpu_status = "Норма" if gpu.gpu_util_percent < 90 else "Высокая нагрузка"
                gpu_util = gpu.gpu_util_percent
                vram_used = gpu.vram_used_mb
                vram_total = gpu.vram_total_mb
                gpu_temp = gpu.temperature_c
            except Exception:
                gpu_status = "Источник GPU не подключён"

        cpu_status = "Высокая нагрузка" if base.cpu_percent >= 85 else "Норма"
        processes_status = "Норма" if base.processes else "Данные процессов пока недоступны"
        if not base.processes:
            error_message = error_message or "Данные процессов пока недоступны"

        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        return TelemetrySnapshot(
            cpu_percent=base.cpu_percent,
            cpu_logical_cores=base.cpu_logical_cores,
            cpu_status=cpu_status,
            ram_used_bytes=base.ram_used_bytes,
            ram_total_bytes=base.ram_total_bytes,
            ram_percent=base.ram_percent,
            gpu_status=gpu_status,
            gpu_util_percent=gpu_util,
            vram_used_mb=vram_used,
            vram_total_mb=vram_total,
            gpu_temperature_c=gpu_temp,
            processes=tuple(
                TelemetryProcessRow(
                    pid=item.pid,
                    name=item.name,
                    cpu_percent=item.cpu_percent,
                    ram_percent=item.ram_percent,
                )
                for item in base.processes
            ),
            processes_status=processes_status,
            status="Телеметрия активна",
            last_updated_at=now,
            error_message=error_message,
        )

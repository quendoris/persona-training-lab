from __future__ import annotations

from persona_training_lab.application.ports.telemetry import (
    BaseTelemetryMetrics,
    GpuTelemetryMetrics,
    ProcessMetrics,
)
from persona_training_lab.application.telemetry.service import (
    SystemTelemetryService,
)


class _BaseProvider:
    def __init__(
        self,
        *,
        cpu_percent: float = 42.0,
        processes: tuple[ProcessMetrics, ...] = (),
    ) -> None:
        self.cpu_percent = cpu_percent
        self.processes = processes

    def collect_base_metrics(self) -> BaseTelemetryMetrics:
        return BaseTelemetryMetrics(
            cpu_percent=self.cpu_percent,
            cpu_logical_cores=16,
            ram_used_bytes=8 * 1024**3,
            ram_total_bytes=16 * 1024**3,
            ram_percent=50.0,
            processes=self.processes,
        )


class _FailingBaseProvider:
    def collect_base_metrics(self) -> BaseTelemetryMetrics:
        raise RuntimeError("base telemetry unavailable")


class _GpuProvider:
    def __init__(self, *, utilization: float = 37.0) -> None:
        self.utilization = utilization

    def collect_gpu_metrics(self) -> GpuTelemetryMetrics:
        return GpuTelemetryMetrics(
            gpu_util_percent=self.utilization,
            vram_used_mb=4096.0,
            vram_total_mb=8192.0,
            temperature_c=61.0,
        )


class _FailingGpuProvider:
    def collect_gpu_metrics(self) -> GpuTelemetryMetrics:
        raise RuntimeError("gpu telemetry unavailable")


def _processes() -> tuple[ProcessMetrics, ...]:
    return (
        ProcessMetrics(
            pid=123,
            name="worker",
            cpu_percent=72.5,
            ram_percent=12.0,
        ),
    )


def test_base_provider_failure_returns_safe_refresh_failed_snapshot() -> None:
    snapshot = SystemTelemetryService(
        system_provider=_FailingBaseProvider(),
        gpu_provider=_GpuProvider(),
    ).collect_snapshot()

    assert snapshot.error_code == "refresh_failed"
    assert snapshot.status_code == "active"
    assert snapshot.cpu_percent == 0.0
    assert snapshot.cpu_logical_cores == 0
    assert snapshot.gpu_status_code == "gpu_unavailable"
    assert snapshot.gpu_util_percent is None
    assert snapshot.processes_status_code == "processes_unavailable"
    assert snapshot.processes == ()


def test_gpu_failure_preserves_successful_base_metrics() -> None:
    snapshot = SystemTelemetryService(
        system_provider=_BaseProvider(processes=_processes()),
        gpu_provider=_FailingGpuProvider(),
    ).collect_snapshot()

    assert snapshot.error_code == ""
    assert snapshot.cpu_percent == 42.0
    assert snapshot.ram_percent == 50.0
    assert snapshot.processes_status_code == "normal"
    assert snapshot.processes[0].pid == 123
    assert snapshot.gpu_status_code == "gpu_unavailable"
    assert snapshot.gpu_util_percent is None


def test_empty_process_sample_is_reported_without_discarding_metrics() -> None:
    snapshot = SystemTelemetryService(
        system_provider=_BaseProvider(processes=()),
        gpu_provider=_GpuProvider(),
    ).collect_snapshot()

    assert snapshot.error_code == "processes_unavailable"
    assert snapshot.cpu_percent == 42.0
    assert snapshot.gpu_status_code == "normal"
    assert snapshot.processes_status_code == "processes_unavailable"
    assert snapshot.processes == ()


def test_high_load_thresholds_are_cpu_85_and_gpu_90_percent() -> None:
    below = SystemTelemetryService(
        system_provider=_BaseProvider(
            cpu_percent=84.9,
            processes=_processes(),
        ),
        gpu_provider=_GpuProvider(utilization=89.9),
    ).collect_snapshot()
    at_threshold = SystemTelemetryService(
        system_provider=_BaseProvider(
            cpu_percent=85.0,
            processes=_processes(),
        ),
        gpu_provider=_GpuProvider(utilization=90.0),
    ).collect_snapshot()

    assert below.cpu_status_code == "normal"
    assert below.gpu_status_code == "normal"
    assert at_threshold.cpu_status_code == "high_load"
    assert at_threshold.gpu_status_code == "high_load"

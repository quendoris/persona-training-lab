from __future__ import annotations

import subprocess

import pytest

from persona_training_lab.application.ports.telemetry import BaseTelemetryMetrics, GpuTelemetryMetrics, ProcessMetrics
from persona_training_lab.application.telemetry.service import SystemTelemetryService
from persona_training_lab.infrastructure.telemetry.collector import NvidiaSmiTelemetryProvider
from persona_training_lab.ui.viewmodels.telemetry import TelemetryViewModel


class _FakeSystemProvider:
    def collect_base_metrics(self) -> BaseTelemetryMetrics:
        return BaseTelemetryMetrics(
            cpu_percent=42.5,
            cpu_logical_cores=16,
            ram_used_bytes=8 * 1024**3,
            ram_total_bytes=32 * 1024**3,
            ram_percent=25.0,
            processes=(
                ProcessMetrics(pid=100, name="python", cpu_percent=22.0, ram_percent=5.0),
                ProcessMetrics(pid=200, name="worker", cpu_percent=11.0, ram_percent=2.5),
            ),
        )


class _FakeGpuProvider:
    def collect_gpu_metrics(self) -> GpuTelemetryMetrics:
        return GpuTelemetryMetrics(
            gpu_util_percent=66.0,
            vram_used_mb=4096.0,
            vram_total_mb=8192.0,
            temperature_c=68.0,
        )


class _FailingGpuProvider:
    def collect_gpu_metrics(self) -> GpuTelemetryMetrics:
        raise RuntimeError("gpu unavailable")


class _NoProcessSystemProvider:
    def collect_base_metrics(self) -> BaseTelemetryMetrics:
        return BaseTelemetryMetrics(
            cpu_percent=12.0,
            cpu_logical_cores=8,
            ram_used_bytes=2 * 1024**3,
            ram_total_bytes=16 * 1024**3,
            ram_percent=12.5,
            processes=(),
        )


class _FailingSystemProvider:
    def collect_base_metrics(self) -> BaseTelemetryMetrics:
        raise RuntimeError("base unavailable")


def test_fake_provider_returns_valid_snapshot() -> None:
    service = SystemTelemetryService(system_provider=_FakeSystemProvider(), gpu_provider=_FakeGpuProvider())

    snapshot = service.collect_snapshot()
    assert snapshot.cpu_percent == 42.5
    assert snapshot.ram_percent == 25.0
    assert snapshot.gpu_util_percent == 66.0
    assert snapshot.vram_total_mb == 8192.0
    assert snapshot.gpu_temperature_c == 68.0
    assert snapshot.status == "Телеметрия активна"


def test_missing_gpu_provider_is_fail_soft() -> None:
    service = SystemTelemetryService(system_provider=_FakeSystemProvider(), gpu_provider=_FailingGpuProvider())

    snapshot = service.collect_snapshot()
    assert snapshot.gpu_util_percent is None
    assert snapshot.vram_total_mb is None
    assert snapshot.gpu_status == "Источник GPU не подключён"


def test_processes_unavailable_does_not_crash() -> None:
    service = SystemTelemetryService(system_provider=_NoProcessSystemProvider(), gpu_provider=None)

    snapshot = service.collect_snapshot()
    assert snapshot.processes == ()
    assert snapshot.processes_status == "Данные процессов пока недоступны"


def test_provider_error_to_viewmodel_controlled_error() -> None:
    service = SystemTelemetryService(system_provider=_FailingSystemProvider(), gpu_provider=None)

    vm = TelemetryViewModel(telemetry_service=service)
    assert vm.status_title == "Телеметрия активна"
    assert vm.status_error == "Не удалось обновить телеметрию"
    assert vm.processes_rows == ("Данные процессов пока недоступны",)


def test_formatting_cpu_ram_vram_values() -> None:
    service = SystemTelemetryService(system_provider=_FakeSystemProvider(), gpu_provider=_FakeGpuProvider())

    vm = TelemetryViewModel(telemetry_service=service)
    items = vm.metric_items()
    labels = {item.short_label: item for item in items}
    assert labels["CPU"].value_text == "42.5%"
    assert labels["RAM"].tooltip == "8.0 GB / 32.0 GB"
    assert labels["VRAM"].value_text == "4096 / 8192 MB"


def test_nvidia_provider_missing_binary_is_soft_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = NvidiaSmiTelemetryProvider()

    def _raise(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("nvidia-smi")

    monkeypatch.setattr(subprocess, "run", _raise)

    with pytest.raises(RuntimeError, match="Источник GPU не подключён"):
        provider.collect_gpu_metrics()

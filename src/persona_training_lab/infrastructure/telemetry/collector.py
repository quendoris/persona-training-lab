from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from importlib import import_module
import subprocess

from persona_training_lab.application.ports.telemetry import BaseTelemetryMetrics, GpuTelemetryMetrics, ProcessMetrics


_PROCESS_FIELDS = ("pid", "name", "cpu_percent", "memory_percent")


@dataclass(frozen=True, slots=True)
class _MemorySnapshot:
    used: int
    total: int
    percent: float


def _as_float(value: object, default: float = 0.0) -> float:
    if not isinstance(value, (str, int, float)):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _as_int(value: object, default: int = 0) -> int:
    if not isinstance(value, (str, int, float)):
        return default
    try:
        return int(value)
    except ValueError:
        return default


class _PsutilFacade:
    """Normalize the dynamically typed psutil surface at infrastructure ingress."""

    def __init__(self, module: object) -> None:
        self._module = module

    def _call(self, name: str, *args: object, **kwargs: object) -> object:
        candidate = getattr(self._module, name, None)
        if not callable(candidate):
            raise RuntimeError(f"psutil API недоступен: {name}")
        return candidate(*args, **kwargs)

    def cpu_percent(self, *, interval: float) -> float:
        return _as_float(self._call("cpu_percent", interval=interval))

    def cpu_count(self, *, logical: bool) -> int:
        return _as_int(self._call("cpu_count", logical=logical))

    def virtual_memory(self) -> _MemorySnapshot:
        memory = self._call("virtual_memory")
        return _MemorySnapshot(
            used=_as_int(getattr(memory, "used", 0)),
            total=_as_int(getattr(memory, "total", 0)),
            percent=_as_float(getattr(memory, "percent", 0.0)),
        )

    def process_infos(self) -> Iterator[Mapping[str, object]]:
        processes = self._call("process_iter", list(_PROCESS_FIELDS))
        if not isinstance(processes, Iterable):
            raise RuntimeError("psutil process_iter вернул неитерируемое значение")
        for process in processes:
            info = getattr(process, "info", None)
            if not isinstance(info, Mapping):
                continue
            yield {field: info.get(field) for field in _PROCESS_FIELDS}


def _load_psutil() -> _PsutilFacade:
    try:
        return _PsutilFacade(import_module("psutil"))
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("psutil недоступен") from exc


@dataclass(slots=True)
class PsutilTelemetryProvider:
    max_process_rows: int = 5

    def collect_base_metrics(self) -> BaseTelemetryMetrics:
        psutil = _load_psutil()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_logical_cores = psutil.cpu_count(logical=True)
        memory = psutil.virtual_memory()

        processes: list[ProcessMetrics] = []
        try:
            for info in psutil.process_infos():
                processes.append(
                    ProcessMetrics(
                        pid=_as_int(info.get("pid")),
                        name=str(info.get("name") or "unknown"),
                        cpu_percent=_as_float(info.get("cpu_percent")),
                        ram_percent=_as_float(info.get("memory_percent")),
                    )
                )
            processes.sort(key=lambda item: (item.cpu_percent, item.ram_percent), reverse=True)
            processes = processes[: self.max_process_rows]
        except Exception:
            processes = []

        return BaseTelemetryMetrics(
            cpu_percent=cpu_percent,
            cpu_logical_cores=cpu_logical_cores,
            ram_used_bytes=memory.used,
            ram_total_bytes=memory.total,
            ram_percent=memory.percent,
            processes=tuple(processes),
        )


class NvidiaSmiTelemetryProvider:
    def collect_gpu_metrics(self) -> GpuTelemetryMetrics:
        command = [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=1.0)
        except Exception as exc:
            raise RuntimeError("Источник GPU не подключён") from exc

        line = result.stdout.strip().splitlines()[0].strip() if result.stdout.strip() else ""
        if not line:
            raise RuntimeError("Источник GPU не подключён")

        parts = [chunk.strip() for chunk in line.split(",")]
        if len(parts) < 4:
            raise RuntimeError("Источник GPU не подключён")

        gpu_util_percent = float(parts[0])
        vram_used_mb = float(parts[1])
        vram_total_mb = float(parts[2])
        temperature_raw = parts[3]
        temperature_c = float(temperature_raw) if temperature_raw not in {"", "N/A"} else None

        return GpuTelemetryMetrics(
            gpu_util_percent=gpu_util_percent,
            vram_used_mb=vram_used_mb,
            vram_total_mb=vram_total_mb,
            temperature_c=temperature_c,
        )

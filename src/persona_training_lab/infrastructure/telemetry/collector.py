from __future__ import annotations

from dataclasses import dataclass
import subprocess

from persona_training_lab.application.ports.telemetry import BaseTelemetryMetrics, GpuTelemetryMetrics, ProcessMetrics


@dataclass(slots=True)
class PsutilTelemetryProvider:
    max_process_rows: int = 5

    def collect_base_metrics(self) -> BaseTelemetryMetrics:
        try:
            import psutil  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on environment
            raise RuntimeError("psutil недоступен") from exc

        cpu_percent = float(psutil.cpu_percent(interval=0.1))
        cpu_logical_cores = int(psutil.cpu_count(logical=True) or 0)
        memory = psutil.virtual_memory()

        processes: list[ProcessMetrics] = []
        try:
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                info = proc.info
                processes.append(
                    ProcessMetrics(
                        pid=int(info.get("pid", 0) or 0),
                        name=str(info.get("name", "") or "unknown"),
                        cpu_percent=float(info.get("cpu_percent", 0.0) or 0.0),
                        ram_percent=float(info.get("memory_percent", 0.0) or 0.0),
                    )
                )
            processes.sort(key=lambda item: (item.cpu_percent, item.ram_percent), reverse=True)
            processes = processes[: self.max_process_rows]
        except Exception:
            processes = []

        return BaseTelemetryMetrics(
            cpu_percent=cpu_percent,
            cpu_logical_cores=cpu_logical_cores,
            ram_used_bytes=int(memory.used),
            ram_total_bytes=int(memory.total),
            ram_percent=float(memory.percent),
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

from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.telemetry.service import (
    SystemTelemetryService,
    TelemetrySnapshot,
)


@dataclass(slots=True, frozen=True)
class TelemetryMetricView:
    short_label: str
    full_label: str
    value_percent: int
    tooltip: str
    value_text: str


@dataclass(slots=True)
class TelemetryViewModel:
    telemetry_service: SystemTelemetryService
    status_title: str = "Телеметрия"
    status_subtitle: str = "Телеметрия активна"
    status_error: str = ""
    cpu_cores_text: str = "Ядер: —"
    processes_rows: tuple[str, ...] = ()
    _snapshot: TelemetrySnapshot | None = None

    def __post_init__(self) -> None:
        self.refresh()

    @property
    def snapshot(self) -> TelemetrySnapshot | None:
        return self._snapshot

    def refresh(self) -> None:
        snapshot = self.telemetry_service.collect_snapshot()
        self._snapshot = snapshot
        self.status_title = snapshot.status
        self.status_subtitle = f"Последнее обновление: {snapshot.last_updated_at}"
        self.status_error = snapshot.error_message
        self.cpu_cores_text = f"Логические ядра: {snapshot.cpu_logical_cores}"

        if snapshot.processes:
            self.processes_rows = tuple(
                f"PID {item.pid} · {item.name} · CPU {item.cpu_percent:.1f}% · RAM {item.ram_percent:.1f}%"
                for item in snapshot.processes
            )
        else:
            self.processes_rows = ("Данные процессов пока недоступны",)

    def metric_items(self) -> tuple[TelemetryMetricView, ...]:
        snapshot = self._snapshot
        if snapshot is None:
            return ()

        ram_text = f"{self._format_bytes(snapshot.ram_used_bytes)} / {self._format_bytes(snapshot.ram_total_bytes)}"
        if snapshot.vram_used_mb is not None and snapshot.vram_total_mb is not None:
            vram_percent = int(round((snapshot.vram_used_mb / max(snapshot.vram_total_mb, 1.0)) * 100))
            vram_text = f"{snapshot.vram_used_mb:.0f} / {snapshot.vram_total_mb:.0f} MB"
        else:
            vram_percent = 0
            vram_text = "Источник GPU не подключён"

        if snapshot.gpu_temperature_c is None:
            temp_percent = 0
            temp_text = "—"
        else:
            temp_percent = int(min(100, round(snapshot.gpu_temperature_c)))
            temp_text = f"{snapshot.gpu_temperature_c:.0f}°C"

        proc_value = int(min(100, round(snapshot.processes[0].cpu_percent))) if snapshot.processes else 0

        return (
            TelemetryMetricView(
                short_label="CPU",
                full_label="CPU",
                value_percent=int(round(snapshot.cpu_percent)),
                tooltip=f"{snapshot.cpu_status} · {snapshot.cpu_percent:.1f}%",
                value_text=f"{snapshot.cpu_percent:.1f}%",
            ),
            TelemetryMetricView(
                short_label="RAM",
                full_label="RAM",
                value_percent=int(round(snapshot.ram_percent)),
                tooltip=ram_text,
                value_text=f"{snapshot.ram_percent:.1f}%",
            ),
            TelemetryMetricView(
                short_label="GPU",
                full_label="GPU",
                value_percent=int(round(snapshot.gpu_util_percent or 0.0)),
                tooltip=snapshot.gpu_status,
                value_text=(f"{snapshot.gpu_util_percent:.1f}%" if snapshot.gpu_util_percent is not None else "—"),
            ),
            TelemetryMetricView(
                short_label="VRAM",
                full_label="VRAM",
                value_percent=vram_percent,
                tooltip=vram_text,
                value_text=vram_text,
            ),
            TelemetryMetricView(
                short_label="Temp",
                full_label="Темп",
                value_percent=temp_percent,
                tooltip=temp_text,
                value_text=temp_text,
            ),
            TelemetryMetricView(
                short_label="Proc",
                full_label="Проц",
                value_percent=proc_value,
                tooltip=snapshot.processes_status,
                value_text=(f"{proc_value}%" if snapshot.processes else "—"),
            ),
        )

    def _format_bytes(self, value: int) -> str:
        if value <= 0:
            return "0 GB"
        gb = value / (1024**3)
        return f"{gb:.1f} GB"

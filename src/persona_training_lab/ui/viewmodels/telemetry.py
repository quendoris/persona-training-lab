from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.telemetry.service import (
    SystemTelemetryService,
    TelemetrySnapshot,
)
from persona_training_lab.ui.i18n.text import text as localized_text


TELEMETRY_STATUS_KEYS: dict[str, str] = {
    "normal": "panel.telemetry.status.normal",
    "high_load": "panel.telemetry.status.high_load",
    "gpu_unavailable": "panel.telemetry.status.gpu_unavailable",
    "processes_unavailable": "panel.telemetry.status.processes_unavailable",
    "active": "panel.telemetry.status.active",
    "refresh_failed": "panel.telemetry.status.refresh_failed",
}


def telemetry_status_key(code: str) -> str | None:
    return TELEMETRY_STATUS_KEYS.get(code)


def _base_text(key: str, **values: object) -> str:
    return localized_text(None, key, **values)


def _base_status_text(code: str, *, raw: str = "") -> str:
    key = telemetry_status_key(code)
    if key is not None:
        return _base_text(key)
    if raw and raw != code:
        return raw
    return code.replace("_", " ").title()


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
    status_title: str = ""
    status_subtitle: str = ""
    status_error: str = ""
    cpu_cores_text: str = ""
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
        self.status_title = _base_status_text(
            snapshot.status_code,
            raw=snapshot.status,
        )
        self.status_subtitle = _base_text(
            "panel.telemetry.updated_at",
            time=snapshot.last_updated_at,
        )
        self.status_error = (
            _base_status_text(
                snapshot.error_code,
                raw=snapshot.error_message,
            )
            if snapshot.error_code
            else snapshot.error_message
        )
        self.cpu_cores_text = _base_text(
            "panel.telemetry.logical_cores",
            cores=snapshot.cpu_logical_cores,
        )

        if snapshot.processes:
            self.processes_rows = tuple(
                _base_text(
                    "panel.telemetry.process_row",
                    pid=item.pid,
                    name=item.name,
                    cpu=f"{item.cpu_percent:.1f}",
                    ram=f"{item.ram_percent:.1f}",
                )
                for item in snapshot.processes
            )
        else:
            self.processes_rows = (
                _base_status_text(
                    snapshot.processes_status_code,
                    raw=snapshot.processes_status,
                ),
            )

    def metric_items(self) -> tuple[TelemetryMetricView, ...]:
        snapshot = self._snapshot
        if snapshot is None:
            return ()

        ram_text = (
            f"{self._format_bytes(snapshot.ram_used_bytes)} / "
            f"{self._format_bytes(snapshot.ram_total_bytes)}"
        )
        if (
            snapshot.vram_used_mb is not None
            and snapshot.vram_total_mb is not None
        ):
            vram_percent = int(
                round(
                    (
                        snapshot.vram_used_mb
                        / max(snapshot.vram_total_mb, 1.0)
                    )
                    * 100
                )
            )
            vram_text = (
                f"{snapshot.vram_used_mb:.0f} / "
                f"{snapshot.vram_total_mb:.0f} MB"
            )
        else:
            vram_percent = 0
            vram_text = _base_status_text(snapshot.gpu_status_code)

        if snapshot.gpu_temperature_c is None:
            temp_percent = 0
            temp_text = "—"
        else:
            temp_percent = int(
                min(100, round(snapshot.gpu_temperature_c))
            )
            temp_text = f"{snapshot.gpu_temperature_c:.0f}°C"

        proc_value = (
            int(min(100, round(snapshot.processes[0].cpu_percent)))
            if snapshot.processes
            else 0
        )

        return (
            TelemetryMetricView(
                short_label="CPU",
                full_label="CPU",
                value_percent=int(round(snapshot.cpu_percent)),
                tooltip=(
                    f"{_base_status_text(snapshot.cpu_status_code, raw=snapshot.cpu_status)}"
                    f" · {snapshot.cpu_percent:.1f}%"
                ),
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
                tooltip=_base_status_text(
                    snapshot.gpu_status_code,
                    raw=snapshot.gpu_status,
                ),
                value_text=(
                    f"{snapshot.gpu_util_percent:.1f}%"
                    if snapshot.gpu_util_percent is not None
                    else "—"
                ),
            ),
            TelemetryMetricView(
                short_label="VRAM",
                full_label="VRAM",
                value_percent=vram_percent,
                tooltip=vram_text,
                value_text=vram_text,
            ),
            TelemetryMetricView(
                short_label=_base_text(
                    "panel.telemetry.metric.temperature.short"
                ),
                full_label=_base_text(
                    "panel.telemetry.metric.temperature.full"
                ),
                value_percent=temp_percent,
                tooltip=temp_text,
                value_text=temp_text,
            ),
            TelemetryMetricView(
                short_label=_base_text(
                    "panel.telemetry.metric.process.short"
                ),
                full_label=_base_text(
                    "panel.telemetry.metric.process.full"
                ),
                value_percent=proc_value,
                tooltip=_base_status_text(
                    snapshot.processes_status_code,
                    raw=snapshot.processes_status,
                ),
                value_text=(
                    f"{proc_value}%" if snapshot.processes else "—"
                ),
            ),
        )

    @staticmethod
    def _format_bytes(value: int) -> str:
        if value <= 0:
            return "0 GB"
        gb = value / (1024**3)
        return f"{gb:.1f} GB"

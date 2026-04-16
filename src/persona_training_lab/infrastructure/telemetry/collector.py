from __future__ import annotations


class NullTelemetryCollector:
    def collect_sample(self) -> dict[str, float | int | str | None]:
        return {
            "cpu_util": None,
            "ram_used_mb": None,
            "gpu_util": None,
            "vram_used_mb": None,
        }

from typing import Protocol


class TelemetryCollectorPort(Protocol):
    def collect_sample(self) -> dict[str, float | int | str | None]: ...

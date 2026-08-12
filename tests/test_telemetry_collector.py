from __future__ import annotations

from persona_training_lab.infrastructure.telemetry.collector import (
    PsutilTelemetryProvider,
    _PsutilFacade,
)


class _Memory:
    used = 6_000
    total = 10_000
    percent = 60.0


class _Process:
    def __init__(
        self,
        *,
        pid: int,
        name: str,
        cpu_percent: float,
        memory_percent: float,
    ) -> None:
        self.info = {
            "pid": pid,
            "name": name,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
        }


class _FakePsutil:
    def cpu_percent(self, *, interval: float) -> float:
        assert interval == 0.1
        return 37.5

    def cpu_count(self, *, logical: bool) -> int:
        assert logical is True
        return 12

    def virtual_memory(self) -> _Memory:
        return _Memory()

    def process_iter(self, fields: list[str]) -> list[_Process]:
        assert fields == ["pid", "name", "cpu_percent", "memory_percent"]
        return [
            _Process(
                pid=1,
                name="low",
                cpu_percent=2.0,
                memory_percent=1.0,
            ),
            _Process(
                pid=2,
                name="high-cpu",
                cpu_percent=80.0,
                memory_percent=3.0,
            ),
            _Process(
                pid=3,
                name="high-ram",
                cpu_percent=10.0,
                memory_percent=50.0,
            ),
        ]


def test_psutil_facade_normalizes_dynamic_module_and_provider_limits_rows(
    monkeypatch,
) -> None:
    facade = _PsutilFacade(_FakePsutil())
    monkeypatch.setattr(
        "persona_training_lab.infrastructure.telemetry.collector._load_psutil",
        lambda: facade,
    )

    metrics = PsutilTelemetryProvider(max_process_rows=2).collect_base_metrics()

    assert metrics.cpu_percent == 37.5
    assert metrics.cpu_logical_cores == 12
    assert metrics.ram_used_bytes == 6_000
    assert metrics.ram_total_bytes == 10_000
    assert metrics.ram_percent == 60.0
    assert [process.pid for process in metrics.processes] == [2, 3]
    assert [process.name for process in metrics.processes] == [
        "high-cpu",
        "high-ram",
    ]

from __future__ import annotations

import json

import pytest

import persona_training_lab.application.experiments.service as experiments_service
from persona_training_lab.application.experiments.service import load_portrait_test_cases


def test_load_portrait_test_cases_from_versioned_jsonl() -> None:
    cases = load_portrait_test_cases()

    assert len(cases) == 10
    assert cases[0].battery_version == "big_five_short_v1"
    assert cases[0].instrument == "BIG_FIVE_SHORT"
    assert cases[0].scoring_version == "big_five_score_v1"
    assert cases[0].trait == "Extraversion"
    assert cases[0].key == "E1"
    assert cases[0].reverse is False
    assert "SCORE: <1-5>" in cases[0].prompt


def test_load_portrait_test_cases_contains_reverse_items() -> None:
    cases = load_portrait_test_cases()

    reverse_keys = {case.key for case in cases if case.reverse}
    assert {"E2R", "A2R", "C2R", "S2R", "O2R"}.issubset(reverse_keys)



class _BatteryResource:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def read_text(self, *, encoding: str) -> str:
        assert encoding == "utf-8"
        return self._payload


class _BatteryRoot:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def joinpath(self, _resource_name: str) -> _BatteryResource:
        return _BatteryResource(self._payload)


@pytest.mark.parametrize(
    ("field", "changed_value"),
    (
        ("battery_version", "big_five_short_v2"),
        ("instrument", "OTHER_INSTRUMENT"),
        ("scoring_version", "big_five_score_v2"),
    ),
)
def test_battery_loader_rejects_mixed_protocol_identity(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    changed_value: str,
) -> None:
    first = {
        "battery_version": "big_five_short_v1",
        "instrument": "BIG_FIVE_SHORT",
        "scoring_version": "big_five_score_v1",
        "trait": "Extraversion",
        "key": "E1",
        "item": "Starts conversations.",
    }
    second = {
        **first,
        "key": "E2",
        "item": "Avoids conversations.",
        field: changed_value,
    }
    payload = "\n".join(
        json.dumps(item, ensure_ascii=False)
        for item in (first, second)
    )
    monkeypatch.setattr(
        experiments_service,
        "files",
        lambda _package: _BatteryRoot(payload),
    )

    with pytest.raises(ValueError, match="mixed protocol identity"):
        load_portrait_test_cases("mixed.jsonl")

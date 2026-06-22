from __future__ import annotations

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

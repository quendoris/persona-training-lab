from __future__ import annotations

import sys

import pytest

from tools.release_gate import ReleaseGate, _parse_args


def _gate_for_policy(*, quick: bool) -> ReleaseGate:
    gate = object.__new__(ReleaseGate)
    gate._quick = quick
    return gate


def test_full_release_profile_always_blocks_on_mypy_and_build() -> None:
    gate = _gate_for_policy(quick=False)

    setup_names = tuple(step.name for step in gate._setup_steps())
    final_names = tuple(step.name for step in gate._final_steps())

    assert setup_names == ("compileall", "ruff", "typing-audit", "mypy")
    assert final_names == ("i18n-audit", "codebase-stats", "build")
    assert all(step.blocking for step in gate._setup_steps())
    assert all(step.blocking for step in gate._final_steps())


def test_quick_release_profile_is_explicitly_smaller_than_full() -> None:
    gate = _gate_for_policy(quick=True)

    assert tuple(step.name for step in gate._setup_steps()) == (
        "compileall",
        "ruff",
        "typing-audit",
    )
    assert tuple(step.name for step in gate._final_steps()) == (
        "i18n-audit",
        "codebase-stats",
    )


@pytest.mark.parametrize(
    "removed_flag",
    ("--strict-mypy", "--skip-mypy", "--skip-build"),
)
def test_release_gate_rejects_removed_typing_and_build_bypasses(
    monkeypatch: pytest.MonkeyPatch,
    removed_flag: str,
) -> None:
    monkeypatch.setattr(sys, "argv", ["release_gate.py", removed_flag])

    with pytest.raises(SystemExit) as error:
        _parse_args()

    assert error.value.code == 2

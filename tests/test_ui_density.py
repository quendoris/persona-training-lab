from __future__ import annotations

from persona_training_lab.ui.density import compute_ui_scale, scaled


def test_compute_ui_scale_compact_notebook() -> None:
    scale, name = compute_ui_scale(1366, 768)
    assert name == "compact-xs"
    assert scale < 0.85


def test_compute_ui_scale_2k_desktop_is_comfortable() -> None:
    scale, name = compute_ui_scale(2560, 1440)
    assert name == "large"
    assert scale >= 1.0


def test_scaled_respects_bounds() -> None:
    assert scaled(320, 0.5, minimum=248, maximum=330) == 248
    assert scaled(320, 2.0, minimum=248, maximum=330) == 330

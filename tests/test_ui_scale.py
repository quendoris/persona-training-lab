from persona_training_lab.config.ui_scale import compute_ui_scale


def test_compute_ui_scale_thresholds() -> None:
    assert compute_ui_scale(800) == 0.82
    assert compute_ui_scale(900) == 0.88
    assert compute_ui_scale(1080) == 0.94
    assert compute_ui_scale(1200) == 1.0
    assert compute_ui_scale(1400) == 1.05

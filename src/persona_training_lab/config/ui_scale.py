from __future__ import annotations


def compute_ui_scale(screen_height: int) -> float:
    if screen_height <= 800:
        return 0.82
    if screen_height <= 900:
        return 0.88
    if screen_height <= 1080:
        return 0.94
    if screen_height <= 1200:
        return 1.0
    return 1.05

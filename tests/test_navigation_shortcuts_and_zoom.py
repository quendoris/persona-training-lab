from __future__ import annotations

from persona_training_lab.ui.agents.version_graph_free_zoom import VersionGraphCanvas
from persona_training_lab.ui.shell.main_window_context import TAB_SHORTCUTS


def test_every_registered_workspace_has_unique_alt_shortcut() -> None:
    expected = {
        "dashboard",
        "profiles",
        "agents",
        "datasets",
        "training",
        "snapshots",
        "tests",
        "analysis",
        "style",
        "docs",
        "keybindings",
    }
    screens = {screen for screen, _sequence in TAB_SHORTCUTS}
    sequences = [sequence for _screen, sequence in TAB_SHORTCUTS]

    assert screens == expected
    assert len(sequences) == len(set(sequences))
    assert all(sequence.startswith("Alt+") for sequence in sequences)


def test_lineage_zoom_range_is_wide_but_bounded() -> None:
    assert VersionGraphCanvas.MIN_ZOOM <= 0.25
    assert VersionGraphCanvas.MAX_ZOOM >= 8.0
    assert VersionGraphCanvas.ZOOM_FACTOR > 1.0

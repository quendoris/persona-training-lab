from __future__ import annotations

from pathlib import Path

from persona_training_lab.ui.agents.version_graph_free_zoom import VersionGraphCanvas
from persona_training_lab.ui.dashboard.screen import DashboardScreen
from persona_training_lab.ui.keybindings.definitions import AGENT_GRAPH_KEY_BINDINGS
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.shell.main_window_context import TAB_SHORTCUTS


def test_every_registered_workspace_has_unique_editable_alt_shortcut() -> None:
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
    definitions = {
        definition.binding_id: definition
        for definition in AGENT_GRAPH_KEY_BINDINGS
    }
    screens = {screen for _binding_id, screen in TAB_SHORTCUTS}
    sequences = [
        definitions[binding_id].sequence
        for binding_id, _screen in TAB_SHORTCUTS
    ]

    assert screens == expected
    assert len(sequences) == len(set(sequences))
    assert all(sequence.startswith("Alt+") for sequence in sequences)
    assert all(
        definitions[binding_id].category == "Навигация по вкладкам"
        for binding_id, _screen in TAB_SHORTCUTS
    )
    assert all(
        definitions[binding_id].editable
        for binding_id, _screen in TAB_SHORTCUTS
    )


def test_navigation_shortcut_rebinds_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "bindings.json"
    manager = KeyBindingManager(storage_path=path)

    result = manager.set_sequence("nav_agents", "Alt+G")

    assert result.accepted
    assert result.changed
    assert manager.sequence("nav_agents") == "Alt+G"
    restored = KeyBindingManager(storage_path=path)
    assert restored.sequence("nav_agents") == "Alt+G"


def test_navigation_shortcut_conflicts_are_rejected(tmp_path: Path) -> None:
    manager = KeyBindingManager(storage_path=tmp_path / "bindings.json")

    result = manager.set_sequence("nav_agents", manager.sequence("nav_training"))

    assert not result.accepted
    assert result.conflict_binding_id == "nav_training"
    assert manager.sequence("nav_agents") == "Alt+A"


def test_dashboard_steps_route_to_their_real_workspaces() -> None:
    assert DashboardScreen._target_for_step("Добавьте датасет") == (
        "datasets",
        "Добав",
    )
    assert DashboardScreen._target_for_step("Доведите training run до artifact") == (
        "training",
        "Запуст",
    )
    assert DashboardScreen._target_for_step(
        "Зарегистрируйте artifact как снимок модели"
    ) == (
        "snapshots",
        "",
    )
    assert DashboardScreen._target_for_step("Соберите портрет") == (
        "tests",
        "Собрать портрет",
    )
    assert DashboardScreen._target_for_step("Откройте Анализ и смотрите delta") == (
        "analysis",
        "",
    )
    assert DashboardScreen._lineage_target("Snapshot · mdl_001") == (
        "snapshots",
        "",
    )


def test_lineage_zoom_range_is_wide_but_bounded() -> None:
    assert VersionGraphCanvas.MIN_ZOOM <= 0.25
    assert VersionGraphCanvas.MAX_ZOOM >= 8.0
    assert VersionGraphCanvas.ZOOM_FACTOR > 1.0

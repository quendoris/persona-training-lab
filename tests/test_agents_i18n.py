from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.application.lineage.atomic_projection import (
    AtomicLineageSnapshot,
)
from persona_training_lab.application.lineage.projection import (
    LineageProjectionService,
)
from persona_training_lab.application.lineage.snapshot import (
    LineageSourceSnapshot,
)
from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.agents import AgentsScreen
from persona_training_lab.ui.agents import screen_lineage_base
from persona_training_lab.ui.agents import version_graph_persistent
from persona_training_lab.ui.agents.lineage_state_atomic import (
    AtomicLineageStateStore,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.keybindings.manager import KeyBindingManager


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


class _AtomicViewModel:
    lineage_loader_factory = None
    lineage_error_reporter = None

    def build_lineage_snapshot(self) -> AtomicLineageSnapshot:
        return AtomicLineageSnapshot(
            source=LineageSourceSnapshot(),
            projection=LineageProjectionService().build_projection(),
        )


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _localization(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> LocalizationManager:
    localization = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    monkeypatch.setattr(
        localization,
        "_prepare_qt_translator",
        lambda _locale: None,
    )
    return localization


def _screen(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[QApplication, LocalizationManager, KeyBindingManager, AgentsScreen]:
    app = _app()
    state_path = tmp_path / "lineage_state.json"
    layout_path = tmp_path / "lineage_layout.json"
    monkeypatch.setattr(
        screen_lineage_base,
        "AtomicLineageStateStore",
        lambda: AtomicLineageStateStore(state_path),
    )
    monkeypatch.setattr(
        version_graph_persistent.VersionGraphCanvas,
        "_default_layout_path",
        lambda _self: layout_path,
    )
    localization = _localization(app, monkeypatch)
    bindings = KeyBindingManager(
        storage_path=tmp_path / "key_bindings.json"
    )
    screen = AgentsScreen(
        _AtomicViewModel(),
        bindings,
        localization=localization,
    )
    return app, localization, bindings, screen


def test_agents_live_language_switch_preserves_lineage_runtime_state(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, localization, bindings, screen = _screen(
        tmp_path,
        monkeypatch,
    )

    branch_id = screen._state.continue_from(
        "snapshot",
        screen._layout_snapshot(),
    )
    screen._selected_node_id = branch_id
    screen._refresh_lineage(center=False)
    screen._graph.restore_layout_snapshot(
        {
            "schema": 1,
            "offsets": {branch_id: {"x": 37.0, "y": -19.0}},
        }
    )
    screen._select_node(branch_id)

    state_before = screen._state.capture_transaction_state()
    layout_before = screen._layout_snapshot()
    projection_before = screen._real_projection_signature
    selected_before = screen._selected_node_id
    bindings_before = bindings.current_bindings()
    mouse_before = bindings.current_mouse_bindings()
    history_before = screen._state.history_toggle_parts()

    assert screen._header_title.text() == "Agents"
    assert screen._details_card.title_label is not None
    assert screen._details_card.title_label.text() == "Version details"
    assert screen._graph._menu_actions()[0][1] == "Make current"
    assert screen._graph._history_action_text == "Undo: create branch"

    branch = screen._node_by_id(branch_id)
    assert branch is not None
    assert isinstance(branch.title, UserMessage)
    assert isinstance(branch.status, UserMessage)

    localization.set_locale("ru-RU", persist=False)

    assert screen._header_title.text() == "Агенты"
    assert screen._details_card.title_label.text() == "Карточка версии"
    assert screen._graph._menu_actions()[0][1] == "Сделать актуальной"
    assert screen._graph._history_action_text == "Отменить: создание ветки"
    assert screen._state.capture_transaction_state() == state_before
    assert screen._layout_snapshot() == layout_before
    assert screen._real_projection_signature == projection_before
    assert screen._selected_node_id == selected_before
    assert bindings.current_bindings() == bindings_before
    assert bindings.current_mouse_bindings() == mouse_before
    assert screen._state.history_toggle_parts() == history_before

    localization.set_locale("en-US", persist=False)

    assert screen._header_title.text() == "Agents"
    assert screen._details_card.title_label.text() == "Version details"
    assert screen._graph._menu_actions()[0][1] == "Make current"
    assert screen._graph._history_action_text == "Undo: create branch"
    assert screen._state.capture_transaction_state() == state_before
    assert screen._layout_snapshot() == layout_before
    assert screen._real_projection_signature == projection_before
    assert screen._selected_node_id == selected_before
    assert bindings.current_bindings() == bindings_before
    assert bindings.current_mouse_bindings() == mouse_before
    assert screen._state.history_toggle_parts() == history_before

    persisted = json.loads(
        (tmp_path / "lineage_state.json").read_text(encoding="utf-8")
    )
    serialized = json.dumps(persisted, ensure_ascii=False)
    assert persisted["schema"] == 6
    assert '"status":' not in serialized
    assert '"subtitle":' not in serialized
    assert '"label":' not in serialized

    screen.deleteLater()
    app.processEvents()


def test_atomic_projection_text_is_semantic_before_ui_rendering(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _localization, _bindings, screen = _screen(
        tmp_path,
        monkeypatch,
    )

    snapshot = screen._node_by_id("snapshot")
    assert snapshot is not None
    assert isinstance(snapshot.title, UserMessage)
    assert isinstance(snapshot.subtitle, UserMessage)
    assert isinstance(snapshot.status, UserMessage)

    detail = screen._real_projection.details["snapshot"]
    assert isinstance(detail.title, UserMessage)
    assert isinstance(detail.body, UserMessage)
    assert all(isinstance(item, UserMessage) for item in detail.checks)

    screen.deleteLater()
    app.processEvents()

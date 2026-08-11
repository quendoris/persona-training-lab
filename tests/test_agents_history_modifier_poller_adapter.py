from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.ui.agents.history_gesture_core import HistoryGestureCore
from persona_training_lab.ui.agents.history_shortcut_routing import (
    HistoryShortcutRouting,
)
from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


class _ModifierPollTransport:
    def __init__(self) -> None:
        self.active_requests: list[bool] = []

    def set_active(self, active: bool) -> None:
        self.active_requests.append(bool(active))


class _OwnershipProbe:
    def __init__(self) -> None:
        self.snapshots: list[dict[str, str]] = []

    def sync(self, sequences: dict[str, str]) -> frozenset[str]:
        self.snapshots.append(dict(sequences))
        return frozenset(sequences)


def test_modifier_polling_tracks_screen_readiness_and_binding_ownership() -> None:
    transport = _ModifierPollTransport()
    active = [True]
    core = HistoryGestureCore()
    core.set_guarded_bindings(("history_toggle",))
    screen = SimpleNamespace(
        _modifier_poll=transport,
        _history_gesture=core,
        _history_keys_are_active=lambda: active[0],
    )

    AgentsScreen._sync_modifier_polling(screen)  # type: ignore[arg-type]

    active[0] = False
    AgentsScreen._sync_modifier_polling(screen)  # type: ignore[arg-type]

    active[0] = True
    core.set_guarded_bindings(())
    AgentsScreen._sync_modifier_polling(screen)  # type: ignore[arg-type]

    assert transport.active_requests == [True, False, False]


def test_modifier_polling_sync_is_safe_before_transport_construction() -> None:
    core = HistoryGestureCore()
    core.set_guarded_bindings(("history_toggle",))
    screen = SimpleNamespace(
        _history_gesture=core,
        _history_keys_are_active=lambda: True,
    )

    AgentsScreen._sync_modifier_polling(screen)  # type: ignore[arg-type]


def test_binding_changes_resync_modifier_poller_after_ownership() -> None:
    calls: list[str] = []
    sequences = dict(HistoryShortcutRouting.default_sequences)
    ownership = _OwnershipProbe()
    screen = SimpleNamespace(
        _reset_history_gesture=lambda: None,
        _shortcut_bindings=SimpleNamespace(sync=lambda: sequences),
        _history_binding_ownership=ownership,
        _sync_modifier_polling=lambda: calls.append("sync"),
    )

    AgentsScreen._apply_key_binding_sequences(screen)  # type: ignore[arg-type]

    assert ownership.snapshots == [sequences]
    assert calls == ["sync"]

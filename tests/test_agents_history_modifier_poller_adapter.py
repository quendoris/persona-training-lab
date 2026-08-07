from __future__ import annotations

from types import SimpleNamespace

from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


class _ModifierPollTransport:
    def __init__(self) -> None:
        self.active_requests: list[bool] = []

    def set_active(self, active: bool) -> None:
        self.active_requests.append(bool(active))


def test_modifier_polling_tracks_screen_readiness_and_binding_ownership() -> None:
    transport = _ModifierPollTransport()
    active = [True]
    guarded = {"history_toggle"}
    screen = SimpleNamespace(
        _modifier_poll=transport,
        _guarded_history_bindings=guarded,
        _history_keys_are_active=lambda: active[0],
    )

    AgentsScreen._sync_modifier_polling(screen)  # type: ignore[arg-type]

    active[0] = False
    AgentsScreen._sync_modifier_polling(screen)  # type: ignore[arg-type]

    active[0] = True
    guarded.clear()
    AgentsScreen._sync_modifier_polling(screen)  # type: ignore[arg-type]

    assert transport.active_requests == [True, False, False]


def test_modifier_polling_sync_is_safe_before_transport_construction() -> None:
    screen = SimpleNamespace(
        _guarded_history_bindings={"history_toggle"},
        _history_keys_are_active=lambda: True,
    )

    AgentsScreen._sync_modifier_polling(screen)  # type: ignore[arg-type]


def test_shortcut_routing_resyncs_modifier_poller_after_ownership_changes() -> None:
    calls: list[str] = []
    sequences = dict(AgentsScreen._DEFAULT_GUARDED_SEQUENCES)
    manager = SimpleNamespace(sequence=lambda binding_id: sequences[binding_id])
    screen = SimpleNamespace(
        _key_binding_manager=manager,
        _HISTORY_BINDING_IDS=AgentsScreen._HISTORY_BINDING_IDS,
        _guarded_history_bindings=set(),
        _shortcuts={},
        _sync_modifier_polling=lambda: calls.append("sync"),
    )

    AgentsScreen._sync_history_shortcut_routing(screen)  # type: ignore[arg-type]

    assert screen._guarded_history_bindings == set(AgentsScreen._HISTORY_BINDING_IDS)
    assert calls == ["sync"]

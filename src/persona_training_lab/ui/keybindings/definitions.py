from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass


def _base_text(key: str) -> str:
    """Render a compatibility label lazily without catalog I/O at import time."""

    from persona_training_lab.ui.i18n.text import text as localized_text

    return localized_text(None, key)


@dataclass(frozen=True, slots=True)
class KeyBindingDefinition:
    binding_id: str
    sequence: str
    auto_repeat: bool = False
    editable: bool = True
    category_id: str = "history"

    @property
    def title_key(self) -> str:
        return f"keybindings.binding.{self.binding_id}.title"

    @property
    def description_key(self) -> str:
        return f"keybindings.binding.{self.binding_id}.description"

    @property
    def category_key(self) -> str:
        return f"keybindings.category.{self.category_id}"

    @property
    def title(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return _base_text(self.title_key)

    @property
    def description(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return _base_text(self.description_key)

    @property
    def category(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return _base_text(self.category_key)


@dataclass(frozen=True, slots=True)
class MouseBindingDefinition:
    binding_id: str
    button: str
    modifier: str
    trigger: str
    target: str
    category_id: str = "mouse"

    @property
    def title_key(self) -> str:
        return f"keybindings.mouse_binding.{self.binding_id}.title"

    @property
    def description_key(self) -> str:
        return f"keybindings.mouse_binding.{self.binding_id}.description"

    @property
    def category_key(self) -> str:
        return f"keybindings.category.{self.category_id}"

    @property
    def title(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return _base_text(self.title_key)

    @property
    def description(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return _base_text(self.description_key)

    @property
    def category(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return _base_text(self.category_key)


MOUSE_BUTTON_IDS = (
    "left",
    "right",
    "middle",
    "back",
    "forward",
    "wheel",
)
MOUSE_MODIFIER_IDS = (
    "none",
    "shift",
    "control",
    "alt",
    "meta",
)


class _LocalizedLabelMap(Mapping[str, str]):
    """Read-only base-locale labels rendered only when actually read."""

    def __init__(self, ids: tuple[str, ...], key_prefix: str) -> None:
        self._ids = ids
        self._id_set = frozenset(ids)
        self._key_prefix = key_prefix

    def __getitem__(self, key: str) -> str:
        if key not in self._id_set:
            raise KeyError(key)
        return _base_text(f"{self._key_prefix}.{key}")

    def __iter__(self) -> Iterator[str]:
        return iter(self._ids)

    def __len__(self) -> int:
        return len(self._ids)


# Compatibility mappings for callers that still expect base-locale labels.
# Catalog access is deliberately lazy so importing the binding model cannot fail
# merely because a presentation catalog is malformed.
MOUSE_BUTTON_LABELS: Mapping[str, str] = _LocalizedLabelMap(
    MOUSE_BUTTON_IDS,
    "keybindings.mouse.button",
)
MOUSE_MODIFIER_LABELS: Mapping[str, str] = _LocalizedLabelMap(
    MOUSE_MODIFIER_IDS,
    "keybindings.mouse.modifier",
)


_GRAPH_BINDING_IDS = frozenset(
    {"delete_branch", "history_toggle", "undo_only"}
)


AGENT_GRAPH_KEY_BINDINGS: tuple[KeyBindingDefinition, ...] = (
    KeyBindingDefinition(
        binding_id="delete_branch",
        sequence="Del",
    ),
    KeyBindingDefinition(
        binding_id="history_toggle",
        sequence="Ctrl+Z",
    ),
    KeyBindingDefinition(
        binding_id="undo_only",
        sequence="Ctrl+Shift+Z",
        auto_repeat=True,
    ),
    KeyBindingDefinition(
        binding_id="nav_dashboard",
        sequence="Alt+H",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_profiles",
        sequence="Alt+P",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_agents",
        sequence="Alt+A",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_datasets",
        sequence="Alt+D",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_training",
        sequence="Alt+T",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_snapshots",
        sequence="Alt+S",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_tests",
        sequence="Alt+E",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_analysis",
        sequence="Alt+L",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_style",
        sequence="Alt+Y",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_docs",
        sequence="Alt+O",
        category_id="navigation",
    ),
    KeyBindingDefinition(
        binding_id="nav_keybindings",
        sequence="Alt+K",
        category_id="navigation",
    ),
)


AGENT_GRAPH_MOUSE_BINDINGS: tuple[MouseBindingDefinition, ...] = (
    MouseBindingDefinition(
        binding_id="open_node_menu",
        button="left",
        modifier="none",
        trigger="click",
        target="node",
    ),
    MouseBindingDefinition(
        binding_id="close_node_menu",
        button="left",
        modifier="none",
        trigger="click",
        target="canvas",
    ),
    MouseBindingDefinition(
        binding_id="pan_canvas_primary",
        button="left",
        modifier="none",
        trigger="drag",
        target="canvas",
    ),
    MouseBindingDefinition(
        binding_id="pan_canvas_secondary",
        button="right",
        modifier="none",
        trigger="drag",
        target="canvas",
    ),
    MouseBindingDefinition(
        binding_id="move_node",
        button="right",
        modifier="none",
        trigger="drag",
        target="node",
    ),
    MouseBindingDefinition(
        binding_id="move_subtree",
        button="right",
        modifier="shift",
        trigger="drag",
        target="node",
    ),
    MouseBindingDefinition(
        binding_id="zoom_canvas",
        button="wheel",
        modifier="none",
        trigger="wheel",
        target="canvas",
    ),
)


def agent_graph_key_bindings_by_id() -> dict[str, KeyBindingDefinition]:
    return {
        binding.binding_id: binding
        for binding in AGENT_GRAPH_KEY_BINDINGS
        if binding.binding_id in _GRAPH_BINDING_IDS
    }


def agent_graph_mouse_bindings_by_id() -> dict[str, MouseBindingDefinition]:
    return {binding.binding_id: binding for binding in AGENT_GRAPH_MOUSE_BINDINGS}

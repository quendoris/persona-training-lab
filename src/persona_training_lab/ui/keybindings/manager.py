from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QKeySequence

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.i18n.text import (
    render_user_message,
    text as localized_text,
)
from persona_training_lab.ui.keybindings.definitions import (
    AGENT_GRAPH_KEY_BINDINGS,
    AGENT_GRAPH_MOUSE_BINDINGS,
    MOUSE_BUTTON_IDS,
    MOUSE_BUTTON_LABELS,
    MOUSE_MODIFIER_IDS,
    MOUSE_MODIFIER_LABELS,
    KeyBindingDefinition,
    MouseBindingDefinition,
)


@dataclass(frozen=True, slots=True)
class BindingChangeResult:
    accepted: bool
    changed: bool
    sequence: str
    message: UserMessage | None = None
    conflict_binding_id: str = ""
    conflict_title_key: str = ""

    @property
    def error(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return render_user_message(None, self.message or "")

    @property
    def conflict_title(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        if not self.conflict_title_key:
            return ""
        return localized_text(None, self.conflict_title_key)


@dataclass(frozen=True, slots=True)
class MouseBindingValue:
    button: str
    modifier: str = "none"


@dataclass(frozen=True, slots=True)
class MouseBindingChangeResult:
    accepted: bool
    changed: bool
    binding: MouseBindingValue
    message: UserMessage | None = None
    conflict_binding_id: str = ""
    conflict_title_key: str = ""

    @property
    def error(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return render_user_message(None, self.message or "")

    @property
    def conflict_title(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        if not self.conflict_title_key:
            return ""
        return localized_text(None, self.conflict_title_key)


class KeyBindingManager(QObject):
    bindings_changed = Signal()

    _FORMAT_VERSION = 2
    _SUPPORTED_OLD_VERSIONS = frozenset({1})

    def __init__(
        self,
        definitions: Iterable[KeyBindingDefinition] = AGENT_GRAPH_KEY_BINDINGS,
        mouse_definitions: Iterable[MouseBindingDefinition] = AGENT_GRAPH_MOUSE_BINDINGS,
        *,
        storage_path: Path | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._definitions = tuple(definitions)
        self._definitions_by_id = {
            item.binding_id: item for item in self._definitions
        }
        self._mouse_definitions = tuple(mouse_definitions)
        self._mouse_definitions_by_id = {
            item.binding_id: item for item in self._mouse_definitions
        }
        self._storage_path = storage_path or self.default_storage_path()
        self._bindings = self._default_bindings()
        self._mouse_bindings = self._default_mouse_bindings()
        self._last_error_message: UserMessage | None = None
        self._load()

    @staticmethod
    def default_storage_path() -> Path:
        return Path.home() / ".persona_training_lab" / "key_bindings.json"

    @property
    def storage_path(self) -> Path:
        return self._storage_path

    @property
    def last_error_message(self) -> UserMessage | None:
        return self._last_error_message

    @property
    def last_error(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return render_user_message(None, self._last_error_message or "")

    def definitions(self) -> tuple[KeyBindingDefinition, ...]:
        return self._definitions

    def mouse_definitions(self) -> tuple[MouseBindingDefinition, ...]:
        return self._mouse_definitions

    def fixed_input_guide(self) -> tuple[MouseBindingDefinition, ...]:
        # Compatibility for callers created before mouse gestures became editable.
        return self._mouse_definitions

    def definition(self, binding_id: str) -> KeyBindingDefinition:
        return self._definitions_by_id[binding_id]

    def mouse_definition(self, binding_id: str) -> MouseBindingDefinition:
        return self._mouse_definitions_by_id[binding_id]

    def sequence(self, binding_id: str) -> str:
        definition = self._definitions_by_id[binding_id]
        return self._bindings.get(binding_id, definition.sequence)

    def mouse_binding(self, binding_id: str) -> MouseBindingValue:
        definition = self._mouse_definitions_by_id[binding_id]
        return self._mouse_bindings.get(
            binding_id,
            MouseBindingValue(definition.button, definition.modifier),
        )

    def mouse_binding_text(self, binding_id: str) -> str:
        """Base-locale compatibility renderer for legacy callers."""
        binding = self.mouse_binding(binding_id)
        button = MOUSE_BUTTON_LABELS.get(binding.button, binding.button)
        modifier = MOUSE_MODIFIER_LABELS.get(binding.modifier, binding.modifier)
        if binding.modifier == "none":
            return button
        return f"{modifier} + {button}"

    def current_bindings(self) -> dict[str, str]:
        return dict(self._bindings)

    def current_mouse_bindings(self) -> dict[str, MouseBindingValue]:
        return dict(self._mouse_bindings)

    def set_sequence(self, binding_id: str, sequence: str) -> BindingChangeResult:
        definition = self._definitions_by_id.get(binding_id)
        if definition is None:
            return BindingChangeResult(
                False,
                False,
                "",
                message=UserMessage("keybindings.error.unknown_command"),
            )
        if not definition.editable:
            return BindingChangeResult(
                False,
                False,
                self.sequence(binding_id),
                message=UserMessage("keybindings.error.not_editable"),
            )

        normalized = self.normalize_sequence(sequence)
        if not normalized:
            return BindingChangeResult(
                False,
                False,
                self.sequence(binding_id),
                message=UserMessage("keybindings.error.empty_sequence"),
            )

        conflict = self.conflict_for(binding_id, normalized)
        if conflict is not None:
            return BindingChangeResult(
                False,
                False,
                self.sequence(binding_id),
                message=UserMessage("keybindings.error.sequence_conflict"),
                conflict_binding_id=conflict.binding_id,
                conflict_title_key=conflict.title_key,
            )

        previous = self.sequence(binding_id)
        if previous == normalized:
            return BindingChangeResult(True, False, normalized)

        updated = dict(self._bindings)
        updated[binding_id] = normalized
        message = self._write(updated, self._mouse_bindings)
        if message is not None:
            return BindingChangeResult(
                False,
                False,
                previous,
                message=message,
            )

        self._bindings = updated
        self._last_error_message = None
        self.bindings_changed.emit()
        return BindingChangeResult(True, True, normalized)

    def set_mouse_binding(
        self,
        binding_id: str,
        button: str,
        modifier: str,
    ) -> MouseBindingChangeResult:
        definition = self._mouse_definitions_by_id.get(binding_id)
        previous = self._mouse_bindings.get(
            binding_id,
            MouseBindingValue("left", "none"),
        )
        if definition is None:
            return MouseBindingChangeResult(
                False,
                False,
                previous,
                message=UserMessage("keybindings.error.unknown_mouse_gesture"),
            )

        normalized_button = button.strip().casefold()
        normalized_modifier = modifier.strip().casefold() or "none"
        if normalized_button not in MOUSE_BUTTON_IDS:
            return MouseBindingChangeResult(
                False,
                False,
                previous,
                message=UserMessage("keybindings.error.unknown_mouse_button"),
            )
        if normalized_modifier not in MOUSE_MODIFIER_IDS:
            return MouseBindingChangeResult(
                False,
                False,
                previous,
                message=UserMessage("keybindings.error.unknown_modifier"),
            )
        if definition.trigger == "wheel" and normalized_button != "wheel":
            return MouseBindingChangeResult(
                False,
                False,
                previous,
                message=UserMessage("keybindings.error.wheel_required"),
            )
        if definition.trigger != "wheel" and normalized_button == "wheel":
            return MouseBindingChangeResult(
                False,
                False,
                previous,
                message=UserMessage("keybindings.error.wheel_forbidden"),
            )

        candidate = MouseBindingValue(normalized_button, normalized_modifier)
        conflict = self.mouse_conflict_for(binding_id, candidate)
        if conflict is not None:
            return MouseBindingChangeResult(
                False,
                False,
                previous,
                message=UserMessage("keybindings.error.mouse_conflict"),
                conflict_binding_id=conflict.binding_id,
                conflict_title_key=conflict.title_key,
            )
        if previous == candidate:
            return MouseBindingChangeResult(True, False, candidate)

        updated = dict(self._mouse_bindings)
        updated[binding_id] = candidate
        message = self._write(self._bindings, updated)
        if message is not None:
            return MouseBindingChangeResult(
                False,
                False,
                previous,
                message=message,
            )

        self._mouse_bindings = updated
        self._last_error_message = None
        self.bindings_changed.emit()
        return MouseBindingChangeResult(True, True, candidate)

    def reset_binding(self, binding_id: str) -> BindingChangeResult:
        definition = self._definitions_by_id.get(binding_id)
        if definition is None:
            return BindingChangeResult(
                False,
                False,
                "",
                message=UserMessage("keybindings.error.unknown_command"),
            )
        return self.set_sequence(binding_id, definition.sequence)

    def reset_mouse_binding(self, binding_id: str) -> MouseBindingChangeResult:
        definition = self._mouse_definitions_by_id.get(binding_id)
        if definition is None:
            return MouseBindingChangeResult(
                False,
                False,
                MouseBindingValue("left", "none"),
                message=UserMessage("keybindings.error.unknown_mouse_gesture"),
            )
        return self.set_mouse_binding(
            binding_id,
            definition.button,
            definition.modifier,
        )

    def reset_all(self) -> BindingChangeResult:
        defaults = self._default_bindings()
        mouse_defaults = self._default_mouse_bindings()
        if defaults == self._bindings and mouse_defaults == self._mouse_bindings:
            return BindingChangeResult(True, False, "")
        message = self._write(defaults, mouse_defaults)
        if message is not None:
            return BindingChangeResult(False, False, "", message=message)
        self._bindings = defaults
        self._mouse_bindings = mouse_defaults
        self._last_error_message = None
        self.bindings_changed.emit()
        return BindingChangeResult(True, True, "")

    def conflict_for(
        self,
        binding_id: str,
        sequence: str,
    ) -> KeyBindingDefinition | None:
        normalized = self.normalize_sequence(sequence)
        if not normalized:
            return None
        comparison = normalized.casefold()
        for definition in self._definitions:
            if definition.binding_id == binding_id or not definition.editable:
                continue
            if self.sequence(definition.binding_id).casefold() == comparison:
                return definition
        return None

    def mouse_conflict_for(
        self,
        binding_id: str,
        candidate: MouseBindingValue,
    ) -> MouseBindingDefinition | None:
        definition = self._mouse_definitions_by_id.get(binding_id)
        if definition is None:
            return None
        for other in self._mouse_definitions:
            if other.binding_id == binding_id or other.target != definition.target:
                continue
            current = self.mouse_binding(other.binding_id)
            if current != candidate:
                continue
            if other.trigger == definition.trigger:
                return other
            # Canvas click and canvas drag intentionally share one button: a small
            # movement separates click from pan. Node click and node drag remain
            # separate because the current graph opens a menu on release.
            if definition.target == "node":
                return other
        return None

    @staticmethod
    def normalize_sequence(sequence: str) -> str:
        parsed = QKeySequence.fromString(
            sequence.strip(),
            QKeySequence.SequenceFormat.PortableText,
        )
        return parsed.toString(QKeySequence.SequenceFormat.PortableText).strip()

    def _default_bindings(self) -> dict[str, str]:
        return {
            item.binding_id: self.normalize_sequence(item.sequence)
            for item in self._definitions
        }

    def _default_mouse_bindings(self) -> dict[str, MouseBindingValue]:
        return {
            item.binding_id: MouseBindingValue(item.button, item.modifier)
            for item in self._mouse_definitions
        }

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._last_error_message = UserMessage(
                "keybindings.error.read",
                {"error": str(exc)},
            )
            return
        if not isinstance(payload, dict):
            self._last_error_message = UserMessage(
                "keybindings.error.unsupported_format"
            )
            return
        version = payload.get("version")
        if (
            version != self._FORMAT_VERSION
            and version not in self._SUPPORTED_OLD_VERSIONS
        ):
            self._last_error_message = UserMessage(
                "keybindings.error.unsupported_format"
            )
            return

        raw_bindings = payload.get("bindings")
        if isinstance(raw_bindings, dict):
            self._bindings = self._load_keyboard_bindings(raw_bindings)

        if version == self._FORMAT_VERSION:
            raw_mouse = payload.get("mouse_bindings")
            if isinstance(raw_mouse, dict):
                self._mouse_bindings = self._load_mouse_bindings(raw_mouse)

    def _load_keyboard_bindings(self, raw_bindings: dict) -> dict[str, str]:
        defaults = self._default_bindings()
        loaded = dict(defaults)
        for definition in self._definitions:
            candidate = raw_bindings.get(
                definition.binding_id,
                definition.sequence,
            )
            if not isinstance(candidate, str):
                continue
            normalized = self.normalize_sequence(candidate)
            if normalized:
                loaded[definition.binding_id] = normalized

        groups: dict[str, list[str]] = {}
        for binding_id, sequence in loaded.items():
            groups.setdefault(sequence.casefold(), []).append(binding_id)
        if any(len(ids) > 1 for ids in groups.values()):
            self._last_error_message = UserMessage(
                "keybindings.error.keyboard_conflicts_repaired"
            )
            return defaults
        return loaded

    def _load_mouse_bindings(
        self,
        raw_bindings: dict,
    ) -> dict[str, MouseBindingValue]:
        defaults = self._default_mouse_bindings()
        loaded = dict(defaults)
        for definition in self._mouse_definitions:
            raw = raw_bindings.get(definition.binding_id)
            if not isinstance(raw, dict):
                continue
            button = raw.get("button")
            modifier = raw.get("modifier", "none")
            if not isinstance(button, str) or not isinstance(modifier, str):
                continue
            button = button.casefold()
            modifier = modifier.casefold()
            if button not in MOUSE_BUTTON_IDS or modifier not in MOUSE_MODIFIER_IDS:
                continue
            if definition.trigger == "wheel" and button != "wheel":
                continue
            if definition.trigger != "wheel" and button == "wheel":
                continue
            loaded[definition.binding_id] = MouseBindingValue(button, modifier)

        previous = self._mouse_bindings
        self._mouse_bindings = loaded
        try:
            for definition in self._mouse_definitions:
                candidate = loaded[definition.binding_id]
                if (
                    self.mouse_conflict_for(definition.binding_id, candidate)
                    is not None
                ):
                    self._last_error_message = UserMessage(
                        "keybindings.error.mouse_conflicts_repaired"
                    )
                    return defaults
        finally:
            self._mouse_bindings = previous
        return loaded

    def _write(
        self,
        bindings: dict[str, str],
        mouse_bindings: dict[str, MouseBindingValue],
    ) -> UserMessage | None:
        payload = {
            "version": self._FORMAT_VERSION,
            "bindings": bindings,
            "mouse_bindings": {
                binding_id: {
                    "button": binding.button,
                    "modifier": binding.modifier,
                }
                for binding_id, binding in sorted(mouse_bindings.items())
            },
        }
        temporary = self._storage_path.with_name(
            f"{self._storage_path.name}.tmp"
        )
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temporary.replace(self._storage_path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            self._last_error_message = UserMessage(
                "keybindings.error.write",
                {"error": str(exc)},
            )
            return self._last_error_message
        return None

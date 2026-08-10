from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.i18n.text import (
    render_user_message,
    text as localized_text,
)
from persona_training_lab.ui.keybindings.definitions import (
    MOUSE_BUTTON_IDS,
    MOUSE_MODIFIER_IDS,
)
from persona_training_lab.ui.keybindings.manager import (
    KeyBindingManager,
    MouseBindingValue,
)


@dataclass(frozen=True, slots=True)
class DraftChangeResult:
    accepted: bool
    changed: bool
    message: UserMessage | None = None

    @property
    def error(self) -> str:
        """Base-locale compatibility surface for legacy callers."""
        return render_user_message(None, self.message or "")


class KeyBindingDraftSession:
    """Editable key-binding snapshot with deferred conflict resolution.

    The manager remains the source of active bindings. Draft values may be
    temporarily invalid; they are committed atomically only when every
    keyboard and mouse conflict has been resolved.
    """

    def __init__(self, manager: KeyBindingManager) -> None:
        self._manager = manager
        self._active_bindings = manager.current_bindings()
        self._active_mouse_bindings = manager.current_mouse_bindings()
        self._draft_bindings = dict(self._active_bindings)
        self._draft_mouse_bindings = dict(self._active_mouse_bindings)

    @property
    def is_dirty(self) -> bool:
        return (
            self._draft_bindings != self._active_bindings
            or self._draft_mouse_bindings != self._active_mouse_bindings
        )

    @property
    def has_conflicts(self) -> bool:
        return bool(self.keyboard_conflicts() or self.mouse_conflicts())

    def sequence(self, binding_id: str) -> str:
        return self._draft_bindings[binding_id]

    def mouse_binding(self, binding_id: str) -> MouseBindingValue:
        return self._draft_mouse_bindings[binding_id]

    def mouse_binding_text(self, binding_id: str) -> str:
        """Base-locale compatibility renderer for legacy callers."""
        binding = self.mouse_binding(binding_id)
        button = localized_text(
            None,
            f"keybindings.mouse.button.{binding.button}",
        )
        modifier = localized_text(
            None,
            f"keybindings.mouse.modifier.{binding.modifier}",
        )
        if binding.modifier == "none":
            return button
        return f"{modifier} + {button}"

    def set_sequence(self, binding_id: str, sequence: str) -> DraftChangeResult:
        definition = self._manager.definition(binding_id)
        if not definition.editable:
            return DraftChangeResult(
                False,
                False,
                UserMessage("keybindings.error.not_editable"),
            )
        normalized = self._manager.normalize_sequence(sequence)
        if not normalized:
            return DraftChangeResult(
                False,
                False,
                UserMessage("keybindings.error.empty_sequence"),
            )
        previous = self._draft_bindings[binding_id]
        if previous == normalized:
            return DraftChangeResult(True, False)
        self._draft_bindings[binding_id] = normalized
        return self._finish_change()

    def set_mouse_binding(
        self,
        binding_id: str,
        button: str,
        modifier: str,
    ) -> DraftChangeResult:
        definition = self._manager.mouse_definition(binding_id)
        normalized_button = button.strip().casefold()
        normalized_modifier = modifier.strip().casefold() or "none"
        if normalized_button not in MOUSE_BUTTON_IDS:
            return DraftChangeResult(
                False,
                False,
                UserMessage("keybindings.error.unknown_mouse_button"),
            )
        if normalized_modifier not in MOUSE_MODIFIER_IDS:
            return DraftChangeResult(
                False,
                False,
                UserMessage("keybindings.error.unknown_modifier"),
            )
        if definition.trigger == "wheel" and normalized_button != "wheel":
            return DraftChangeResult(
                False,
                False,
                UserMessage("keybindings.error.wheel_required"),
            )
        if definition.trigger != "wheel" and normalized_button == "wheel":
            return DraftChangeResult(
                False,
                False,
                UserMessage("keybindings.error.wheel_forbidden"),
            )
        candidate = MouseBindingValue(normalized_button, normalized_modifier)
        if self._draft_mouse_bindings[binding_id] == candidate:
            return DraftChangeResult(True, False)
        self._draft_mouse_bindings[binding_id] = candidate
        return self._finish_change()

    def reset_binding(self, binding_id: str) -> DraftChangeResult:
        definition = self._manager.definition(binding_id)
        return self.set_sequence(binding_id, definition.sequence)

    def reset_mouse_binding(self, binding_id: str) -> DraftChangeResult:
        definition = self._manager.mouse_definition(binding_id)
        return self.set_mouse_binding(
            binding_id,
            definition.button,
            definition.modifier,
        )

    def reset_all(self) -> DraftChangeResult:
        keyboard = {
            definition.binding_id: self._manager.normalize_sequence(
                definition.sequence
            )
            for definition in self._manager.definitions()
        }
        mouse = {
            definition.binding_id: MouseBindingValue(
                definition.button,
                definition.modifier,
            )
            for definition in self._manager.mouse_definitions()
        }
        if (
            keyboard == self._draft_bindings
            and mouse == self._draft_mouse_bindings
        ):
            return DraftChangeResult(True, False)
        self._draft_bindings = keyboard
        self._draft_mouse_bindings = mouse
        return self._finish_change()

    def keyboard_conflicts(self) -> dict[str, tuple[str, ...]]:
        groups: dict[str, list[str]] = {}
        for definition in self._manager.definitions():
            if not definition.editable:
                continue
            sequence = self._draft_bindings[definition.binding_id].casefold()
            groups.setdefault(sequence, []).append(definition.binding_id)
        conflicts: dict[str, tuple[str, ...]] = {}
        for binding_ids in groups.values():
            if len(binding_ids) < 2:
                continue
            for binding_id in binding_ids:
                conflicts[binding_id] = tuple(
                    item for item in binding_ids if item != binding_id
                )
        return conflicts

    def mouse_conflicts(self) -> dict[str, tuple[str, ...]]:
        definitions = self._manager.mouse_definitions()
        conflicts: dict[str, set[str]] = {}
        for index, definition in enumerate(definitions):
            candidate = self._draft_mouse_bindings[definition.binding_id]
            for other in definitions[index + 1 :]:
                if other.target != definition.target:
                    continue
                if self._draft_mouse_bindings[other.binding_id] != candidate:
                    continue
                same_trigger = other.trigger == definition.trigger
                ambiguous_node_gesture = definition.target == "node"
                if not same_trigger and not ambiguous_node_gesture:
                    continue
                conflicts.setdefault(definition.binding_id, set()).add(
                    other.binding_id
                )
                conflicts.setdefault(other.binding_id, set()).add(
                    definition.binding_id
                )
        return {
            binding_id: tuple(sorted(other_ids))
            for binding_id, other_ids in conflicts.items()
        }

    def conflict_text(self, binding_id: str, *, mouse: bool) -> str:
        """Base-locale compatibility renderer for legacy callers."""
        conflicts = self.mouse_conflicts() if mouse else self.keyboard_conflicts()
        partner_ids = conflicts.get(binding_id, ())
        if not partner_ids:
            return ""
        if mouse:
            titles = [
                self._manager.mouse_definition(item).title
                for item in partner_ids
            ]
        else:
            titles = [
                self._manager.definition(item).title
                for item in partner_ids
            ]
        rendered_titles = ", ".join(f"«{title}»" for title in titles)
        return localized_text(
            None,
            "keybindings.conflict.with",
            titles=rendered_titles,
        )

    def discard_conflicting_changes(self) -> DraftChangeResult:
        keyboard_ids = set(self.keyboard_conflicts())
        mouse_ids = set(self.mouse_conflicts())
        if not keyboard_ids and not mouse_ids:
            return DraftChangeResult(True, False)
        for binding_id in keyboard_ids:
            self._draft_bindings[binding_id] = self._active_bindings[binding_id]
        for binding_id in mouse_ids:
            self._draft_mouse_bindings[binding_id] = (
                self._active_mouse_bindings[binding_id]
            )
        return self._commit_if_valid()

    def discard_all(self) -> None:
        self._draft_bindings = dict(self._active_bindings)
        self._draft_mouse_bindings = dict(self._active_mouse_bindings)

    def rebase_if_clean(self) -> None:
        if self.is_dirty:
            return
        self._active_bindings = self._manager.current_bindings()
        self._active_mouse_bindings = self._manager.current_mouse_bindings()
        self._draft_bindings = dict(self._active_bindings)
        self._draft_mouse_bindings = dict(self._active_mouse_bindings)

    def _finish_change(self) -> DraftChangeResult:
        if self.has_conflicts:
            return DraftChangeResult(True, True)
        return self._commit_if_valid()

    def _commit_if_valid(self) -> DraftChangeResult:
        if self.has_conflicts:
            return DraftChangeResult(True, True)
        if not self.is_dirty:
            return DraftChangeResult(True, False)

        # One atomic write is essential for swaps and multi-step conflict
        # resolution: no intermediate invalid mapping becomes active.
        message = self._manager._write(  # noqa: SLF001
            self._draft_bindings,
            self._draft_mouse_bindings,
        )
        if message is not None:
            return DraftChangeResult(False, True, message)

        self._manager._bindings = dict(self._draft_bindings)  # noqa: SLF001
        self._manager._mouse_bindings = dict(  # noqa: SLF001
            self._draft_mouse_bindings
        )
        self._manager._last_error_message = None  # noqa: SLF001
        self._active_bindings = dict(self._draft_bindings)
        self._active_mouse_bindings = dict(self._draft_mouse_bindings)
        self._manager.bindings_changed.emit()
        return DraftChangeResult(True, True)

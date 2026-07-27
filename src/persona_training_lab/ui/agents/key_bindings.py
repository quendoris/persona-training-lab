from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyBindingDefinition:
    binding_id: str
    sequence: str
    title: str
    description: str
    auto_repeat: bool = False


AGENT_GRAPH_KEY_BINDINGS: tuple[KeyBindingDefinition, ...] = (
    KeyBindingDefinition(
        binding_id="delete_branch",
        sequence="Del",
        title="Удалить выбранную ветку",
        description="Открывает подтверждение удаления выбранной локальной ветки и её поддерева.",
    ),
    KeyBindingDefinition(
        binding_id="history_toggle",
        sequence="Ctrl+Z",
        title="Отменить или вернуть последнее изменение",
        description="Первое нажатие отменяет последний шаг, второе возвращает его; повторные нажатия переключают состояние до и после.",
    ),
    KeyBindingDefinition(
        binding_id="undo_only",
        sequence="Ctrl+Shift+Z",
        title="Последовательно уходить назад по истории",
        description="Всегда отменяет ещё один шаг; при удержании повторяет отмену по системной частоте клавиатуры.",
        auto_repeat=True,
    ),
)


def agent_graph_key_bindings_by_id() -> dict[str, KeyBindingDefinition]:
    return {binding.binding_id: binding for binding in AGENT_GRAPH_KEY_BINDINGS}

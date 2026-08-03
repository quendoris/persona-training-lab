from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyBindingDefinition:
    binding_id: str
    sequence: str
    title: str
    description: str
    auto_repeat: bool = False
    editable: bool = True
    category: str = "История и ветки"


@dataclass(frozen=True, slots=True)
class InputGuideDefinition:
    guide_id: str
    gesture: str
    title: str
    description: str
    category: str = "Мышь и canvas"


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
        description="Всегда отменяет ещё один шаг; при удержании повторяет отмену.",
        auto_repeat=True,
    ),
)


AGENT_GRAPH_INPUT_GUIDE: tuple[InputGuideDefinition, ...] = (
    InputGuideDefinition(
        guide_id="open_node_menu",
        gesture="ЛКМ по точке",
        title="Открыть действия узла",
        description="Выбирает точку и открывает встроенное меню действий прямо на canvas.",
    ),
    InputGuideDefinition(
        guide_id="close_node_menu",
        gesture="ЛКМ по пустому месту",
        title="Закрыть меню узла",
        description="Скрывает открытое меню, не меняя выбранную точку.",
    ),
    InputGuideDefinition(
        guide_id="pan_canvas",
        gesture="ЛКМ или ПКМ по пустому месту + движение",
        title="Перемещать пространство",
        description="Панорамирует рабочую область графа в пределах динамического canvas.",
    ),
    InputGuideDefinition(
        guide_id="move_node",
        gesture="ПКМ по точке + движение",
        title="Перемещать одну точку",
        description="Меняет ручное положение только выбранного узла.",
    ),
    InputGuideDefinition(
        guide_id="move_subtree",
        gesture="Shift + ПКМ по точке + движение",
        title="Перемещать поддерево",
        description="Переключается динамически и перемещает выбранную точку вместе с дочерними узлами.",
    ),
    InputGuideDefinition(
        guide_id="zoom_canvas",
        gesture="Колесо мыши",
        title="Масштабировать граф",
        description="Изменяет масштаб относительно позиции курсора.",
    ),
)


def agent_graph_key_bindings_by_id() -> dict[str, KeyBindingDefinition]:
    return {binding.binding_id: binding for binding in AGENT_GRAPH_KEY_BINDINGS}


def agent_graph_input_guide_by_id() -> dict[str, InputGuideDefinition]:
    return {guide.guide_id: guide for guide in AGENT_GRAPH_INPUT_GUIDE}

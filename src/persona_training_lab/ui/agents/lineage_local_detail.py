from __future__ import annotations

from persona_training_lab.ui.agents.lineage import LineageVersionNode
from persona_training_lab.ui.viewmodels.agents_contracts import AgentDetailView


def build_local_lineage_detail(node: LineageVersionNode) -> AgentDetailView:
    """Describe a local lineage branch without inventing persisted model metadata."""

    parent_id = node.parent_id or "—"
    return AgentDetailView(
        title=node.title,
        body="\n".join(
            (
                node.subtitle,
                f"Локальный id: {node.node_id}",
                f"Родитель: {parent_id}",
                f"Статус: {node.status}",
            )
        ),
        checks=(
            "Локальная ветка хранится отдельно от зарегистрированной model version.",
            "Training run и artifact считаются связанными только после отдельной регистрации.",
        ),
        actions=(
            "ЛКМ по точке открывает действия на графе.",
            "Del удаляет выбранную локальную ветку.",
            "Ctrl+Z переключает последнее изменение: отменить / вернуть.",
            "Ctrl+Shift+Z всегда уходит ещё на один шаг назад.",
            "ПКМ двигает пространство/точку.",
        ),
    )


__all__ = ("build_local_lineage_detail",)

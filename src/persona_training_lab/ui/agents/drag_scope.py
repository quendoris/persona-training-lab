from __future__ import annotations

from collections.abc import Iterable

from persona_training_lab.ui.i18n.text import text as localized_text


def drag_target_ids(
    node_id: str,
    subtree_ids: Iterable[str],
    *,
    shift_down: bool,
) -> tuple[str, ...]:
    """Choose the nodes moved by the current mouse delta.

    The choice is intentionally evaluated for every mouse move so Shift can be
    pressed or released without ending the right-button drag.
    """

    if not node_id:
        return ()
    if not shift_down:
        return (node_id,)
    targets = tuple(
        dict.fromkeys(str(item) for item in subtree_ids if item)
    )
    return targets or (node_id,)


def drag_history_action_code(
    *,
    moved_node: bool,
    moved_subtree: bool,
) -> str:
    if moved_node and moved_subtree:
        return "layout_move_mixed"
    if moved_subtree:
        return "layout_move_subtree"
    return "layout_move_node"


def drag_history_label(
    *,
    moved_node: bool,
    moved_subtree: bool,
) -> str:
    """Base-locale compatibility label for historical callers."""

    action_code = drag_history_action_code(
        moved_node=moved_node,
        moved_subtree=moved_subtree,
    )
    return localized_text(
        None,
        f"agents.history.action.{action_code}",
    )

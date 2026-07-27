from __future__ import annotations

from collections.abc import Iterable


def drag_target_ids(node_id: str, subtree_ids: Iterable[str], *, shift_down: bool) -> tuple[str, ...]:
    """Choose the nodes moved by the current mouse delta.

    The choice is intentionally evaluated for every mouse move so Shift can be
    pressed or released without ending the right-button drag.
    """

    if not node_id:
        return ()
    if not shift_down:
        return (node_id,)
    targets = tuple(dict.fromkeys(str(item) for item in subtree_ids if item))
    return targets or (node_id,)


def drag_history_label(*, moved_node: bool, moved_subtree: bool) -> str:
    if moved_node and moved_subtree:
        return "перемещение точки и поддерева"
    if moved_subtree:
        return "перемещение поддерева"
    return "перемещение точки"

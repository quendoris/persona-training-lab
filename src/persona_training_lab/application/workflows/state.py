from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

WorkflowStatus = Literal["idle", "running", "completed", "failed"]


@dataclass(slots=True)
class WorkflowRuntimeState:
    workflow_id: str
    workflow_type: str
    status: WorkflowStatus
    current_step: str
    message: str | None = None

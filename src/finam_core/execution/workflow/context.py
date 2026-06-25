# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkflowContext:
    # Контекст выполнения текущей стадии workflow.
    workflow_run_id: int
    candidate_id: str
    symbol: str
    strategy: str
    timeframe: str
    workflow_type: str
    workflow_version: str
    current_stage: str
    next_stage: str | None
    payload: dict[str, Any] = field(default_factory=dict)

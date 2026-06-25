# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkflowResult:
    # Универсальный результат выполнения stage-плагина.
    status: str
    next_stage: str | None
    reason: str
    payload: dict[str, Any] = field(default_factory=dict)

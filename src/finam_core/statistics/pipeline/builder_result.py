# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BuilderResult:
    status: str
    rows_in: int
    rows_out: int
    duplicate_rows: int
    error_rows: int
    health_score: int
    health_light: str
    health_reason_code: str
    reason: str
    payload: dict[str, Any] = field(default_factory=dict)

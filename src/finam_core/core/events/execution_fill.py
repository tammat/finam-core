# -*- coding: utf-8 -*-
"""
ExecutionFill — каноническое событие исполнения (единый источник истины).

Русский коммент:
- Используется в Pipeline B как payload для event {"type":"FILL", "fill": ExecutionFill(...)}.
- Должно быть одно место определения класса, чтобы не ловить несовместимые типы.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True, slots=True)
class ExecutionFill:
    fill_id: str
    symbol: str
    side: str
    qty: float
    price: float
    commission: float = 0.0
    timestamp: datetime = datetime.now(timezone.utc)
    origin: str = "unknown"
    account_id: Optional[str] = None

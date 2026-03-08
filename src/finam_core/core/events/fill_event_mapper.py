# src/finam_core/core/events/fill_event_mapper.py
# Русский коммент: адаптер ExecutionFill -> core FillEvent (для совместимости со старым core).

from __future__ import annotations

from finam_core.core.events.fill_event import FillEvent
from finam_core.execution.execution_fill import ExecutionFill


def to_core_fill_event(x: ExecutionFill) -> FillEvent:
    # Русский коммент: FillEvent принимает timestamp, fill_id и т.п. — даём совместимый набор.
    return FillEvent(
        fill_id=x.fill_id,
        symbol=x.symbol,
        side=x.side,
        qty=float(x.qty),
        price=float(x.price),
        commission=float(x.commission),
        timestamp=x.timestamp,
    )
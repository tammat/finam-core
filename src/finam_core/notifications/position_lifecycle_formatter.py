# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PositionLifecycleAlert:
    event_type: str
    symbol: str
    side: str
    horizon: str
    old_stop: Optional[float] = None
    new_stop: Optional[float] = None
    current_price: Optional[float] = None
    reason: str = ""


def _fmt(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", " ")


def format_position_lifecycle_alert(alert: PositionLifecycleAlert) -> str:
    event_ru = {
        "PIPE_STOP_MOVED": "Стоп перенесён",
        "PIPE_TRAILING_UPDATED": "Trailing-stop обновлён",
        "PIPE_BREAK_EVEN": "Стоп перенесён в безубыток",
        "PIPE_PARTIAL_TAKE": "Частичная фиксация",
        "PIPE_EXIT_SIGNAL": "Сигнал на выход",
    }.get(alert.event_type, alert.event_type)

    lines = [
        "📈 Сопровождение позиции",
        "",
        f"Событие: {event_ru}",
        f"Инструмент: {alert.symbol}",
        f"Направление: {alert.side}",
        f"Тип: {alert.horizon}",
        "",
        f"Старый SL: {_fmt(alert.old_stop)}",
        f"Новый SL: {_fmt(alert.new_stop)}",
        f"Текущая цена: {_fmt(alert.current_price)}",
    ]

    if alert.reason:
        lines.extend(["", f"Причина: {alert.reason}"])

    return "\n".join(lines)

# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ManualPositionPnlAlert:
    symbol: str
    qty: float
    average_price: float
    current_price: float
    price_delta: float
    pnl_pct: float
    status: str
    recommendation: str = ""


def _fmt(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


def format_manual_position_pnl_alert(alert: ManualPositionPnlAlert) -> str:
    status_ru = {
        "PROFIT": "прибыль",
        "LOSS": "убыток",
        "FLAT": "без существенного изменения",
    }.get(alert.status, alert.status)

    lines = [
        "📊 Ручная позиция Finam",
        "",
        f"Инструмент: {alert.symbol}",
        f"Количество: {_fmt(alert.qty)}",
        f"Статус: {status_ru}",
        "",
        f"Средняя цена: {_fmt(alert.average_price)}",
        f"Текущая цена: {_fmt(alert.current_price)}",
        f"Отклонение: {_fmt(alert.price_delta)}",
        f"PnL: {alert.pnl_pct:.2f}%",
    ]

    if alert.recommendation:
        lines.extend(["", f"Рекомендация: {alert.recommendation}"])

    return "\n".join(lines)

# -*- coding: utf-8 -*-
"""
Форматирование торговой точки для Telegram.
Telegram получает НЕ сделки, а только: вход, стоп-лосс, тейк-профит.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SignalAlert:
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    timeframe: str = "M5"
    horizon: str = "INTRADAY"
    reason: str = ""
    confidence: Optional[float] = None
    risk_rub: Optional[float] = None


def _fmt_price(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


def format_signal_alert(alert: SignalAlert) -> str:
    side_ru = {
        "BUY": "ЛОНГ",
        "SELL": "ШОРТ",
    }.get(alert.side.upper(), alert.side.upper())

    risk = abs(alert.entry_price - alert.stop_loss)
    reward = abs(alert.take_profit - alert.entry_price)
    rr = reward / max(risk, 0.000001)

    lines = [
        "📍 Торговая точка",
        "",
        f"Инструмент: {alert.symbol}",
        f"Направление: {side_ru}",
        f"Тип: {alert.horizon}",
        f"Таймфрейм: {alert.timeframe}",
        "",
        f"Вход: {_fmt_price(alert.entry_price)}",
        f"Стоп-лосс: {_fmt_price(alert.stop_loss)}",
        f"Тейк-профит: {_fmt_price(alert.take_profit)}",
        f"RR: {rr:.2f}",
    ]

    if alert.risk_rub is not None:
        lines.append(f"Риск: {_fmt_price(alert.risk_rub)} ₽")

    if alert.confidence is not None:
        lines.append(f"Уверенность: {alert.confidence:.2f}")

    if alert.reason:
        lines.extend(["", f"Основание: {alert.reason}"])

    lines.extend([
        "",
        "⚠️ Это сигнал для ручного решения. Заявка не выставлена.",
    ])

    return "\n".join(lines)

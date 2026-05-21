from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramSignalMessage:
    channel_type: str
    symbol: str
    display_name: str
    direction: str
    source: str
    strategy: str
    timeframe: str
    confidence: float
    entry: float | None = None
    stop: float | None = None
    take: float | None = None
    risk_comment: str = ""
    reason: str = ""


def format_telegram_signal_message(message: TelegramSignalMessage) -> str:
    """
    Русский комментарий:
    Единый формат Telegram-сообщений для REAL / PAPER / RADAR / RISK / REVIEW.
    """

    channel = message.channel_type.upper()
    direction = message.direction.upper()
    confidence_pct = round(float(message.confidence) * 100, 1)

    lines = [
        f"[{channel}][{direction}]",
        "",
        f"Инструмент: {message.symbol}",
        f"Название: {message.display_name}",
        f"Источник: {message.source}",
        f"Стратегия: {message.strategy}",
        f"Таймфрейм: {message.timeframe}",
        f"Уверенность: {confidence_pct}%",
    ]

    if message.entry is not None:
        lines.append(f"Вход: {message.entry}")

    if message.stop is not None:
        lines.append(f"Стоп: {message.stop}")

    if message.take is not None:
        lines.append(f"Цель: {message.take}")

    if message.risk_comment:
        lines.extend(["", f"Риск: {message.risk_comment}"])

    if message.reason:
        lines.extend(["", f"Обоснование: {message.reason}"])

    return "\n".join(lines)

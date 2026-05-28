from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramAdvisoryMessageV1:
    severity: str
    category: str
    symbol: str
    title: str
    body: str


class TelegramAdvisoryFormatterV1:
    """
    Русский комментарий:
    Унифицированный formatter для advisory-сообщений.
    Ничего не отправляет в Telegram.
    Только формирует текст.
    """

    def format_position_advisory(
        self,
        *,
        symbol: str,
        asset_class: str,
        side: str,
        qty: float,
        entry: float,
        current: float,
        pnl: float,
        pnl_day: float,
        stop: float,
        take: float,
        action: str,
    ) -> TelegramAdvisoryMessageV1:
        severity = self._severity_from_action(action)

        title = f"{self._emoji(severity)} {symbol} | {side} | {action}"

        body = "\n".join(
            [
                f"Инструмент: {symbol}",
                f"Класс: {asset_class}",
                f"Сторона: {side}",
                f"Количество: {qty}",
                f"Вход: {entry}",
                f"Текущая цена: {current}",
                f"P&L: {pnl:.2f} ₽",
                f"P&L день: {pnl_day:.2f} ₽",
                f"Стоп: {stop}",
                f"Цель: {take}",
                f"Действие: {self._action_ru(action)}",
            ]
        )

        return TelegramAdvisoryMessageV1(
            severity=severity,
            category="MANUAL_POSITION",
            symbol=symbol,
            title=title,
            body=body,
        )

    def render(self, msg: TelegramAdvisoryMessageV1) -> str:
        return (
            f"{msg.title}\n"
            f"Категория: {msg.category}\n"
            f"Важность: {msg.severity}\n\n"
            f"{msg.body}"
        )

    @staticmethod
    def _severity_from_action(action: str) -> str:
        if action == "REVIEW":
            return "WARNING"
        if action == "REDUCE":
            return "WARNING"
        if action == "HOLD_PROFIT":
            return "INFO"
        return "NORMAL"

    @staticmethod
    def _emoji(severity: str) -> str:
        if severity == "WARNING":
            return "⚠️"
        if severity == "INFO":
            return "✅"
        return "ℹ️"

    @staticmethod
    def _action_ru(action: str) -> str:
        mapping = {
            "REVIEW": "пересмотреть позицию",
            "REDUCE": "сократить риск",
            "HOLD_PROFIT": "удерживать прибыль",
            "HOLD": "удерживать",
        }
        return mapping.get(action, action)

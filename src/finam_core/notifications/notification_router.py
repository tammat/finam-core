# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.notifications.telegram_notifier import TelegramNotifier
from finam_core.notifications.trade_signal_notifier import TradeSignalNotifier


class NotificationRouter:
    """
    Русский комментарий:
    Выбирает Telegram-бота по типу события.
    SYSTEM -> основной TelegramNotifier.
    TRADE/SIGNAL/OUTCOME -> TradeSignalNotifier.
    """

    TRADE_TRIGGERS = {
        "trade_signal",
        "trade_outcome",
        "paper_trade",
        "virtual_trade",
        "entry_signal",
        "exit_signal",
        "pnl_report",
    }

    SYSTEM_TRIGGERS = {
        "system",
        "market_radar",
        "volatility_scan",
        "position_sync",
        "healthcheck",
        "service_status",
    }

    def __init__(self) -> None:
        self.system_notifier = TelegramNotifier()
        self.trade_notifier = TradeSignalNotifier()

    def send(self, *, trigger: str, text: str) -> bool:
        trigger = str(trigger or "system").strip().lower()

        if trigger in self.TRADE_TRIGGERS:
            if hasattr(self.trade_notifier, "send_text"):
                return bool(self.trade_notifier.send_text(text))
            return False

        if hasattr(self.system_notifier, "send"):
            self.system_notifier.send(text)
            return True

        return False

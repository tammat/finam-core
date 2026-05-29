# -*- coding: utf-8 -*-
"""
TradeSignalNotifier

Русский комментарий:
Отдельный Telegram-бот только для торговых сигналов.
Реальные заявки НЕ отправляет.
"""

from __future__ import annotations

import os
import logging
import requests
from finam_core.notifications.telegram_actionable_filter_v1 import TelegramActionableFilterV1

LOG = logging.getLogger(__name__)


class TradeSignalNotifier:

    def __init__(self) -> None:
        self.enabled = (
            os.getenv("ENABLE_TRADE_SIGNAL_ALERTS", "0") == "1"
        )

        self.token = (
            os.getenv("TRADE_TG_BOT_TOKEN", "").strip()
        )

        self.chat_id = (
            os.getenv("TRADE_TG_CHAT_ID", "").strip()
        )

        self.proxy = (
            os.getenv("TRADE_TG_PROXY", "").strip()
        )


    def send_text(self, text: str) -> bool:
        if not TelegramActionableFilterV1().allows(text):
            print(
                "TELEGRAM_ACTIONABLE_FILTER_DROP",
                f"reason={TelegramActionableFilterV1().reason(text)}",
                flush=True,
            )
            return False

        """Русский комментарий: отправляет произвольный текст через отдельного торгового Telegram-бота."""
        if not self.enabled:
            return False

        if not self.token or not self.chat_id:
            return False

        if not str(text or "").strip():
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": str(text).strip(),
        }

        try:
            kwargs = {
                "json": payload,
                "timeout": 10,
            }

            if self.proxy:
                kwargs["proxies"] = {
                    "http": self.proxy,
                    "https": self.proxy,
                }

            r = requests.post(url, **kwargs)

            if r.status_code == 200:
                print("TRADE_SIGNAL_TEXT_SENT", flush=True)
                return True

            LOG.error(f"TRADE_SIGNAL_TEXT_FAILED {r.status_code} {r.text}")
            return False

        except Exception as e:
            LOG.error(f"TRADE_SIGNAL_TEXT_EXCEPTION {e}")
            return False


    def send_signal(
        self,
        symbol: str,
        side: str,
        entry: float,
        stop_loss: float,
        take_profit: float,
        confidence: float = 0.0,
        regime: str = "unknown",
        reason: str = "",
    ) -> bool:

        if not self.enabled:
            return False

        if not self.token or not self.chat_id:
            return False

        rr = 0.0

        try:
            risk = abs(entry - stop_loss)

            if risk > 0:
                rr = abs(take_profit - entry) / risk

        except Exception:
            rr = 0.0

        text = (
            f"📈 TRADE SIGNAL\n\n"
            f"Инструмент: {symbol}\n"
            f"Сторона: {side}\n\n"
            f"Вход: {entry:.4f}\n"
            f"Stop: {stop_loss:.4f}\n"
            f"Take: {take_profit:.4f}\n\n"
            f"RR: {rr:.2f}\n"
            f"Confidence: {confidence:.2f}\n"
            f"Regime: {regime}\n"
            f"Причина: {reason}\n\n"
            f"⚠️ Только сигнал. Заявка НЕ отправлена."
        )

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": text,
        }

        try:

            kwargs = {
                "json": payload,
                "timeout": 10,
            }

            if self.proxy:
                kwargs["proxies"] = {
                    "http": self.proxy,
                    "https": self.proxy,
                }

            r = requests.post(url, **kwargs)

            if r.status_code == 200:
                print(
                    f"TRADE_SIGNAL_SENT symbol={symbol} side={side}",
                    flush=True,
                )
                return True

            LOG.error(
                f"TRADE_SIGNAL_FAILED {r.status_code} {r.text}"
            )

            return False

        except Exception as e:
            LOG.error(f"TRADE_SIGNAL_EXCEPTION {e}")
            return False

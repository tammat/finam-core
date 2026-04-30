# -*- coding: utf-8 -*-
"""
TelegramNotifier — только уведомления.
Русский коммент: notifier не имеет права отправлять торговые заявки.
"""

from __future__ import annotations

import os
import logging
import requests

LOG = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self) -> None:
        self.token = (os.getenv("TG_BOT_TOKEN") or os.getenv("TG_TOKEN") or "").strip()
        self.chat_id = os.getenv("TG_CHAT_ID", "").strip()
        self.enabled = os.getenv("ENABLE_TELEGRAM_NOTIFIER", "0") == "1"
        self.proxy = os.getenv("TG_PROXY", "").strip()

    def send(self, text: str) -> None:
        if not self.enabled or not self.token or not self.chat_id:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
            )
            if resp.status_code != 200:
                LOG.warning("TELEGRAM SEND FAILED status=%s body=%s", resp.status_code, resp.text)
        except Exception as exc:
            # Русский коммент: уведомления не должны ломать торговый pipeline.
            LOG.warning("TELEGRAM SEND EXCEPTION: %s", exc)
            return

    def send_trade_alert(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        source: str = "",
        reason: str = "",
        pnl: float | None = None,
    ) -> None:
        side_ru = "ПОКУПКА" if str(side).upper() == "BUY" else "ПРОДАЖА"
        lines = [
            "📌 <b>Сделка исполнена</b>",
            f"Инструмент: <b>{symbol}</b>",
            f"Сторона: <b>{side_ru}</b>",
            f"Количество: <b>{qty}</b>",
            f"Цена: <b>{price}</b>",
        ]
        if source:
            lines.append(f"Источник сигнала: <b>{source}</b>")
        if reason:
            lines.append(f"Причина: <b>{reason}</b>")
        if pnl is not None:
            lines.append(f"PnL: <b>{pnl:.4f}</b>")
        self.send("\n".join(lines))

    def send_risk_alert(
        self,
        *,
        symbol: str | None,
        layer: str,
        reason: str,
        side: str | None = None,
        qty: float | None = None,
        details: dict | None = None,
    ) -> None:
        lines = [
            "🛑 <b>Сделка заблокирована риск-контролем</b>",
            f"Слой риска: <b>{layer}</b>",
            f"Причина: <b>{reason}</b>",
        ]
        if symbol:
            lines.append(f"Инструмент: <b>{symbol}</b>")
        if side:
            side_ru = "ПОКУПКА" if str(side).upper() == "BUY" else "ПРОДАЖА"
            lines.append(f"Сторона: <b>{side_ru}</b>")
        if qty is not None:
            lines.append(f"Количество: <b>{qty}</b>")
        if details:
            for key, value in details.items():
                lines.append(f"{key}: <b>{value}</b>")
        self.send("\n".join(lines))

    def send_signal_alert(
        self,
        *,
        symbol: str,
        side: str,
        source: str,
        confidence: float | None = None,
        score: float | None = None,
        reason: str = "",
        entry: float | None = None,
        stop: float | None = None,
        take: float | None = None,
        rr: float | None = None,
    ) -> None:
        side_ru = "ЛОНГ" if str(side).upper() == "BUY" else "ШОРТ"

        lines = [
            "🟢 <b>Сигнал</b>",
            f"<b>{symbol}</b> | {side_ru}",
        ]

        # Русский коммент: уровни сделки (ключевой PRO-блок)
        if entry is not None:
            lines.append(f"Вход: <b>{entry:.2f}</b>")
        if stop is not None:
            lines.append(f"Стоп: <b>{stop:.2f}</b>")
        if take is not None:
            lines.append(f"Цель: <b>{take:.2f}</b>")
        if rr is not None:
            lines.append(f"R/R: <b>1:{rr:.2f}</b>")

        # Русский коммент: дополнительные метрики (внизу)
        if confidence is not None:
            lines.append(f"Уверенность: <b>{confidence:.2f}</b>")
        if score is not None:
            lines.append(f"Сила: <b>{score:.2f}</b>")
        if reason:
            lines.append(f"Контекст: <b>{reason}</b>")

        self.send("\n".join(lines))

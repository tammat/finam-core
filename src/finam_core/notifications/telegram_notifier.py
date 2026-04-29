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
                timeout=5,
            )
            if resp.status_code != 200:
                LOG.warning("TELEGRAM SEND FAILED status=%s body=%s", resp.status_code, resp.text)
        except Exception as exc:
            # Русский коммент: уведомления не должны ломать торговый pipeline.
            LOG.warning("TELEGRAM SEND EXCEPTION: %s", exc)
            return

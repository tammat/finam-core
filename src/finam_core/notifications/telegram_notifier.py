# -*- coding: utf-8 -*-
"""
PROD TelegramNotifier
- Загружает .env
- Поддерживает proxy / fallback
- Не падает
- Логирует ошибки
"""

from __future__ import annotations

import os
import logging
import requests
from dotenv import load_dotenv

# === LOAD ENV ===
load_dotenv()

LOG = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self) -> None:
        # токены
        self.token = (
            os.getenv("TG_BOT_TOKEN")
            or os.getenv("TG_TOKEN")
            or ""
        ).strip()

        self.chat_id = os.getenv("TG_CHAT_ID", "").strip()
        self.enabled = os.getenv("ENABLE_TELEGRAM_NOTIFIER", "0") == "1"

        # proxy
        self.proxy = os.getenv("TG_PROXY", "").strip()

    def _send_direct(self, payload: dict) -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        try:
            r = requests.post(url, json=payload, timeout=5)
            if r.status_code == 200:
                return True
            else:
                LOG.error(f"TELEGRAM FAILED (direct) {r.status_code} {r.text}")
                return False
        except Exception as e:
            LOG.error(f"TELEGRAM DIRECT EXCEPTION: {e}")
            return False

    def _send_proxy(self, payload: dict) -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        try:
            proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }

            r = requests.post(url, json=payload, proxies=proxies, timeout=7)

            if r.status_code == 200:
                return True
            else:
                LOG.error(f"TELEGRAM FAILED (proxy) {r.status_code} {r.text}")
                return False
        except Exception as e:
            LOG.error(f"TELEGRAM PROXY EXCEPTION: {e}")
            return False

    def send(self, text: str) -> None:
        if not self.enabled:
            return

        if not self.token or not self.chat_id:
            LOG.error("TELEGRAM CONFIG ERROR: token/chat_id missing")
            return

        payload = {
            "chat_id": self.chat_id,
            "text": text,
        }

        # 1️⃣ сначала пробуем напрямую
        if self._send_direct(payload):
            return

        # 2️⃣ fallback через proxy (если есть)
        if self.proxy:
            self._send_proxy(payload)
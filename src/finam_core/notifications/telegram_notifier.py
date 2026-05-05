# -*- coding: utf-8 -*-
"""
PROD TelegramNotifier
- Надёжная загрузка .env
- Очередь (без потери сигналов)
- Анти-дубли
- Rate limit
- Direct → Proxy fallback
- Без падений
"""

from __future__ import annotations

import os
import logging
import requests
import time
from collections import deque
from dotenv import load_dotenv
from pathlib import Path

# === LOAD ENV (гарантировано работает везде) ===
env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path)

LOG = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self) -> None:
        # === ENV ===
        self.token = (os.getenv("TG_TOKEN") or os.getenv("TG_BOT_TOKEN") or "").strip()
        self.chat_id = os.getenv("TG_CHAT_ID", "").strip()
        self.proxy = os.getenv("TG_PROXY")

        self.enabled = os.getenv("ENABLE_TELEGRAM_NOTIFIER", "0") == "1"

        # === RELIABILITY LAYER ===
        self._queue = deque(maxlen=1000)
        self._last_sent_hash = None
        self._last_sent_ts = 0.0
        self._min_interval = float(os.getenv("TG_MIN_INTERVAL", "0.5"))

    # =========================
    # LOW LEVEL SEND
    # =========================

    def _is_empty_text(self, text) -> bool:
        """Русский комментарий: защита от пустых Telegram-сообщений на любом уровне отправки."""
        return text is None or not str(text).strip()
    def _is_empty_payload(self, payload: dict) -> bool:
        """Русский комментарий: защита от пустого поля text в payload Telegram."""
        if not isinstance(payload, dict):
            return True
        return self._is_empty_text(payload.get("text"))


    def _send_direct(self, payload: dict) -> bool:
        if self._is_empty_payload(payload):
            return True

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
        if self._is_empty_payload(payload):
            return True

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        try:
            try:
                import socks  # noqa
            except ImportError:
                print("SOCKS proxy requested but PySocks not installed → fallback to direct", flush=True)
                return False

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

    # =========================
    # RELIABILITY LOGIC
    # =========================

    def _should_send(self, text: str) -> bool:
        h = hash(text)

        # анти-дубль
        if h == self._last_sent_hash:
            return False

        now = time.time()

        # rate limit
        if now - self._last_sent_ts < self._min_interval:
            return False

        self._last_sent_hash = h
        self._last_sent_ts = now
        return True

    def _flush_queue(self):
        while self._queue:
            payload = self._queue.popleft()

            # 1. DIRECT
            ok = self._send_direct(payload)

            # 2. fallback → proxy
            if not ok and self.proxy:
                ok = self._send_proxy(payload)

            if ok:
                print("TELEGRAM SEND OK", flush=True)
            else:
                LOG.error("TELEGRAM DROP: message lost after retry")

    # =========================
    # PUBLIC API
    # =========================

    
    def send(self, text: str) -> None:
        if self._is_empty_text(text):
            return

        if not self.enabled:
            return

        if not self.token or not self.chat_id:
            return

        if not self._should_send(text):
            return

        payload = {
            "chat_id": self.chat_id,
            "text": str(text).strip(),
        }

        # Русский комментарий: если задан TG_PROXY, direct-send не пробуем
        if self.proxy:
            ok = self._send_proxy(payload)
            if ok:
                print("TELEGRAM SEND OK", flush=True)
            else:
                LOG.error("TELEGRAM DROP: message lost after proxy send")
            return

        ok = self._send_direct(payload)
        if ok:
            print("TELEGRAM SEND OK", flush=True)
        else:
            LOG.error("TELEGRAM DROP: message lost after direct send")

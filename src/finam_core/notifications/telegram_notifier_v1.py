from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramNotifyResultV1:
    dry_run: bool
    sent: bool
    chat_id: str
    text_len: int
    status_code: int | None
    error: str | None


class TelegramNotifierV1:
    """
    Русский комментарий:
    Реальный Telegram notifier для advisory-сообщений.
    По умолчанию работает в dry-run режиме.
    Реальная отправка разрешена только при TELEGRAM_NOTIFY_DRY_RUN=0.
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        chat_id: str | None = None,
        dry_run: bool | None = None,
        timeout_sec: float = 10.0,
    ) -> None:
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.timeout_sec = timeout_sec

        if dry_run is None:
            dry_run = os.getenv("TELEGRAM_NOTIFY_DRY_RUN", "1") != "0"

        self.dry_run = bool(dry_run)

    def send_text(self, text: str) -> TelegramNotifyResultV1:
        text = str(text or "")

        if not text.strip():
            print("TELEGRAM_NOTIFY_SKIP reason=empty_text", flush=True)
            return TelegramNotifyResultV1(
                dry_run=self.dry_run,
                sent=False,
                chat_id=self.chat_id,
                text_len=0,
                status_code=None,
                error="empty_text",
            )

        if self.dry_run:
            print(
                "TELEGRAM_NOTIFY_DRY_RUN",
                f"chat_id={self.chat_id or 'EMPTY'}",
                f"text_len={len(text)}",
                flush=True,
            )
            return TelegramNotifyResultV1(
                dry_run=True,
                sent=False,
                chat_id=self.chat_id,
                text_len=len(text),
                status_code=None,
                error=None,
            )

        if not self.token:
            print("TELEGRAM_NOTIFY_FAILED reason=missing_token", flush=True)
            return TelegramNotifyResultV1(
                dry_run=False,
                sent=False,
                chat_id=self.chat_id,
                text_len=len(text),
                status_code=None,
                error="missing_token",
            )

        if not self.chat_id:
            print("TELEGRAM_NOTIFY_FAILED reason=missing_chat_id", flush=True)
            return TelegramNotifyResultV1(
                dry_run=False,
                sent=False,
                chat_id=self.chat_id,
                text_len=len(text),
                status_code=None,
                error="missing_chat_id",
            )

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        payload = urllib.parse.urlencode(
            {
                "chat_id": self.chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                status_code = int(response.status)
                raw_body = response.read().decode("utf-8", errors="replace")
                body = json.loads(raw_body) if raw_body else {}

            ok = bool(body.get("ok")) and 200 <= status_code < 300

            print(
                "TELEGRAM_NOTIFY_RESULT",
                f"sent={ok}",
                f"status_code={status_code}",
                f"chat_id={self.chat_id}",
                f"text_len={len(text)}",
                flush=True,
            )

            return TelegramNotifyResultV1(
                dry_run=False,
                sent=ok,
                chat_id=self.chat_id,
                text_len=len(text),
                status_code=status_code,
                error=None if ok else str(body),
            )

        except urllib.error.HTTPError as exc:
            error_text = exc.read().decode("utf-8", errors="replace")
            print(
                "TELEGRAM_NOTIFY_FAILED",
                f"status_code={exc.code}",
                f"error={error_text}",
                flush=True,
            )
            return TelegramNotifyResultV1(
                dry_run=False,
                sent=False,
                chat_id=self.chat_id,
                text_len=len(text),
                status_code=int(exc.code),
                error=error_text,
            )

        except Exception as exc:
            print(
                "TELEGRAM_NOTIFY_FAILED",
                f"error={type(exc).__name__}:{exc}",
                flush=True,
            )
            return TelegramNotifyResultV1(
                dry_run=False,
                sent=False,
                chat_id=self.chat_id,
                text_len=len(text),
                status_code=None,
                error=f"{type(exc).__name__}:{exc}",
            )

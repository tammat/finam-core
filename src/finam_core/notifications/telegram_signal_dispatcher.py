from __future__ import annotations

from dataclasses import dataclass
import os
import requests

from finam_core.notifications.telegram_signal_router import route_telegram_signal
from finam_core.notifications.telegram_signal_taxonomy import (
    TelegramSignalMessage,
    format_telegram_signal_message,
)


@dataclass(frozen=True)
class TelegramSignalDispatchResult:
    status: str
    channel_type: str
    target_env: str
    chat_id: str
    reason: str


class TelegramSignalDispatcher:
    """
    Русский комментарий:
    Единый отправитель Telegram-сообщений REAL/PAPER/RADAR/RISK/REVIEW.
    """

    def __init__(self, token_env: str = "TELEGRAM_BOT_TOKEN") -> None:
        self.token_env = token_env

    def dispatch(self, message: TelegramSignalMessage) -> TelegramSignalDispatchResult:
        route = route_telegram_signal(
            channel_type=message.channel_type,
            confidence=message.confidence,
        )

        if not route.should_send:
            return TelegramSignalDispatchResult(
                status="SKIPPED",
                channel_type=route.channel_type,
                target_env=route.target_env,
                chat_id="",
                reason=route.reason,
            )

        token = os.getenv(self.token_env, "").strip()
        chat_id = os.getenv(route.target_env, "").strip()

        if not token:
            return TelegramSignalDispatchResult(
                status="SKIPPED",
                channel_type=route.channel_type,
                target_env=route.target_env,
                chat_id=chat_id,
                reason="не_задан_TELEGRAM_BOT_TOKEN",
            )

        if not chat_id:
            return TelegramSignalDispatchResult(
                status="SKIPPED",
                channel_type=route.channel_type,
                target_env=route.target_env,
                chat_id="",
                reason=f"не_задан_{route.target_env}",
            )

        text = format_telegram_signal_message(message)

        url = f"https://api.telegram.org/bot{token}/sendMessage"

        try:
            response = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            response.raise_for_status()
        except Exception as exc:
            return TelegramSignalDispatchResult(
                status="ERROR",
                channel_type=route.channel_type,
                target_env=route.target_env,
                chat_id=chat_id,
                reason=f"{type(exc).__name__}:{exc}",
            )

        return TelegramSignalDispatchResult(
            status="SENT",
            channel_type=route.channel_type,
            target_env=route.target_env,
            chat_id=chat_id,
            reason="сообщение_отправлено",
        )

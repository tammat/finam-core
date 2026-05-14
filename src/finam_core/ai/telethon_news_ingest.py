from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from telethon import TelegramClient, events

from finam_core.ai.sentiment_event_repository import SentimentEventRepository
from finam_core.ai.telegram_sentiment_listener import TelegramSentimentListener


LOG = logging.getLogger("finam_core.ai.telethon_news_ingest")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _parse_channels(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def _build_proxy() -> Any:
    """
    Русский комментарий:
    Telethon использует PySocks-style proxy tuple.
    Для простоты пока SOCKS5 proxy берём из TG_PROXY.
    """
    proxy_url = (os.getenv("TG_MTPROTO_PROXY") or os.getenv("TG_PROXY") or "").strip()
    if not proxy_url:
        return None

    if not proxy_url.startswith("socks5h://"):
        raise RuntimeError("Only socks5h:// TG_MTPROTO_PROXY/TG_PROXY is supported for Telethon")

    import socks
    from urllib.parse import urlparse

    u = urlparse(proxy_url)
    return (
        socks.SOCKS5,
        u.hostname,
        int(u.port or 1080),
        True,
        u.username,
        u.password,
    )


class TelethonNewsIngest:
    """
    Русский комментарий:
    MTProto ingestion layer.

    Только:
    - читает сообщения из заданных Telegram-каналов;
    - передает текст в SentimentEngine;
    - сохраняет AI events в PostgreSQL.

    Не:
    - торгует;
    - вызывает execution;
    - вызывает broker API;
    - формирует заявки.
    """

    def __init__(self) -> None:
        api_id = os.getenv("TG_API_ID", "").strip()
        api_hash = os.getenv("TG_API_HASH", "").strip()
        channels = os.getenv("TG_CHANNELS", "").strip()

        if not api_id or not api_hash:
            raise RuntimeError("TG_API_ID / TG_API_HASH are required")

        if not channels:
            raise RuntimeError("TG_CHANNELS is empty")

        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.channels = _parse_channels(channels)

        self.repository = SentimentEventRepository()
        self.listener = TelegramSentimentListener(repository=self.repository)

        proxy = _build_proxy()

        LOG.info("Telethon using SOCKS proxy=%s", bool(proxy))

        self.client = TelegramClient(
            "finam_ai_news",
            self.api_id,
            self.api_hash,
            proxy=proxy,
        )

    async def start(self) -> None:
        LOG.info("TelethonNewsIngest starting channels=%s", self.channels)

        await self.client.start()

        @self.client.on(events.NewMessage(chats=self.channels))
        async def on_new_message(event) -> None:
            text = (event.raw_text or "").strip()
            if not text:
                return

            if text.startswith("/"):
                return

            chat = await event.get_chat()
            source = getattr(chat, "username", None) or getattr(chat, "title", None) or "telethon"

            result_event = self.listener.analyze_message(
                text=text,
                source=f"telethon:{source}",
            )

            LOG.info(
                "TELETHON_NEWS_INGEST source=%s label=%s score=%.4f text=%r",
                source,
                result_event.label,
                result_event.score,
                text[:160],
            )

        LOG.info("TelethonNewsIngest started")
        await self.client.run_until_disconnected()


async def main_async() -> int:
    configure_logging()
    ingest = TelethonNewsIngest()
    await ingest.start()
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())

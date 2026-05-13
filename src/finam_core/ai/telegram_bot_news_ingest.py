from __future__ import annotations

import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

from finam_core.ai.sentiment_event_repository import SentimentEventRepository
from finam_core.ai.telegram_sentiment_listener import TelegramSentimentListener


LOG = logging.getLogger("finam_core.ai.telegram_bot_news_ingest")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class TelegramBotNewsIngest:
    """
    Русский комментарий:
    Telegram Bot ingestion layer.

    Только:
    - читает сообщения;
    - делает sentiment analysis;
    - пишет AI events в PostgreSQL.

    Не:
    - торгует;
    - отправляет заявки;
    - вызывает execution/broker API.
    """

    def __init__(self) -> None:
        self.bot_token = (
            os.getenv("TG_AI_TOKEN")
            or os.getenv("TG_BOT_TOKEN")
            or ""
        ).strip()

        if not self.bot_token:
            raise RuntimeError("TG_BOT_TOKEN is empty")

        self.repository = SentimentEventRepository()

        self.listener = TelegramSentimentListener(
            repository=self.repository,
        )

    async def on_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        message = update.effective_message

        if message is None:
            return

        text = (message.text or message.caption or "").strip()

        if not text:
            return

        # Русский комментарий:
        # Команды бота не являются новостями и не пишутся в AI sentiment.
        if text.startswith("/"):
            LOG.info("BOT_NEWS_INGEST_SKIP command=%r", text)
            return

        # Русский комментарий:
        # Команды бота не являются новостями и не должны попадать в AI sentiment.
        if text.startswith("/"):
            LOG.info("BOT_NEWS_INGEST_SKIP command=%r", text)
            return

        source = "telegram_bot"

        if message.forward_origin:
            source = "telegram_forward"

        event = self.listener.analyze_message(
            text=text,
            source=source,
        )

        LOG.info(
            "BOT_NEWS_INGEST "
            f"label={event.label} "
            f"score={event.score:.4f} "
            f"text={text[:120]!r}",
        )

    def run(self) -> None:
        app = Application.builder().token(self.bot_token).build()

        app.add_handler(
            MessageHandler(
                filters.TEXT | filters.CaptionRegex(".*"),
                self.on_message,
            )
        )

        LOG.info("TelegramBotNewsIngest started")

        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )


def main() -> int:
    configure_logging()

    ingest = TelegramBotNewsIngest()
    ingest.run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

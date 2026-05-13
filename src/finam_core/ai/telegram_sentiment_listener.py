from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from finam_core.ai.sentiment_engine import SentimentEngine, SentimentResult
from finam_core.ai.sentiment_events import TelegramSentimentEvent
from finam_core.ai.sentiment_event_repository import SentimentEventRepository


LOG = logging.getLogger("finam_core.ai.telegram_sentiment_listener")


class TelegramSentimentListener:
    """
    Русский комментарий:
    Безопасный listener для анализа текстов из Telegram/новостей.

    Ограничения безопасности:
    - не подключается к торговому контуру;
    - не обращается к брокерскому API;
    - не формирует и не отправляет заявки;
    - только анализирует текст и пишет результат в лог.
    """

    def __init__(
        self,
        engine: SentimentEngine | None = None,
        repository: SentimentEventRepository | None = None,
    ) -> None:
        self.engine = engine or SentimentEngine()
        self.repository = repository

    def analyze_message(self, text: str, source: str = "telegram") -> TelegramSentimentEvent:
        result: SentimentResult = self.engine.analyze(text)

        event = TelegramSentimentEvent(
            ts=datetime.now(timezone.utc).isoformat(),
            source=source,
            text=text,
            label=result.label,
            score=result.score,
            raw=result.raw,
        )

        self.log_event(event)

        if self.repository is not None:
            self.repository.save(event)

        return event

    def log_event(self, event: TelegramSentimentEvent) -> None:
        payload = asdict(event)

        LOG.info(
            "AI_TELEGRAM_SENTIMENT %s",
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
        )


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main() -> int:
    """
    Русский комментарий:
    Smoke-режим. Пока не подключаемся к Telegram API.
    Проверяем только безопасный анализ и логирование.
    """

    configure_logging()

    listener = TelegramSentimentListener()

    samples = [
        "Сбер опубликовал сильную отчетность, рынок позитивно оценивает прибыль.",
        "Нефть резко снижается на опасениях падения спроса.",
        "Компания сообщила операционные результаты без существенных изменений.",
    ]

    for text in samples:
        listener.analyze_message(text=text, source="smoke")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

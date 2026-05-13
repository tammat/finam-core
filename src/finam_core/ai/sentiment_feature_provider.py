from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras

from finam_core.ai.sentiment_event_repository import SentimentEventRepository


@dataclass(frozen=True)
class SentimentFeatures:
    """
    Русский комментарий:
    Безопасный feature-объект для стратегии.
    Не содержит торговых команд.
    """

    ai_sentiment_label: str
    ai_sentiment_score: float
    ai_sentiment_source: str
    ai_sentiment_ts: str | None
    ai_sentiment_symbol: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ai_sentiment_label": self.ai_sentiment_label,
            "ai_sentiment_score": self.ai_sentiment_score,
            "ai_sentiment_source": self.ai_sentiment_source,
            "ai_sentiment_ts": self.ai_sentiment_ts,
            "ai_sentiment_symbol": self.ai_sentiment_symbol,
        }


class SentimentFeatureProvider:
    """
    Русский комментарий:
    Читает последние AI-события из PostgreSQL и отдаёт их как features.
    Не вызывает модель, не читает Telegram, не отправляет заявки.
    """

    def __init__(self, repository: SentimentEventRepository | None = None) -> None:
        self.repository = repository or SentimentEventRepository()

    def latest_for_symbol(self, symbol: str | None = None) -> SentimentFeatures:
        with psycopg2.connect(self.repository.dsn) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if symbol:
                    cur.execute(
                        """
                        SELECT ts, source, symbol, label, score
                        FROM ai_sentiment_events
                        WHERE symbol = %s OR symbol IS NULL
                        ORDER BY
                            CASE WHEN symbol = %s THEN 0 ELSE 1 END,
                            ts DESC,
                            id DESC
                        LIMIT 1
                        """,
                        (symbol, symbol),
                    )
                else:
                    cur.execute(
                        """
                        SELECT ts, source, symbol, label, score
                        FROM ai_sentiment_events
                        ORDER BY ts DESC, id DESC
                        LIMIT 1
                        """
                    )

                row = cur.fetchone()

        if not row:
            return SentimentFeatures(
                ai_sentiment_label="unknown",
                ai_sentiment_score=0.0,
                ai_sentiment_source="none",
                ai_sentiment_ts=None,
                ai_sentiment_symbol=symbol,
            )

        ts = row["ts"]
        if isinstance(ts, datetime):
            ts_value = ts.isoformat()
        else:
            ts_value = str(ts)

        return SentimentFeatures(
            ai_sentiment_label=str(row["label"]),
            ai_sentiment_score=float(row["score"]),
            ai_sentiment_source=str(row["source"]),
            ai_sentiment_ts=ts_value,
            ai_sentiment_symbol=row["symbol"],
        )

    def latest_features_dict(self, symbol: str | None = None) -> dict[str, Any]:
        return self.latest_for_symbol(symbol=symbol).as_dict()

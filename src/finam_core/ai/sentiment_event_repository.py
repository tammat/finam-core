from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any

import psycopg2

from finam_core.ai.sentiment_events import TelegramSentimentEvent


class SentimentEventRepository:
    """
    Русский комментарий:
    Репозиторий сохраняет AI-события в PostgreSQL.
    Торговые заявки не формирует и не отправляет.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or self._build_dsn_from_env()

    @staticmethod
    def _build_dsn_from_env() -> str:
        database_url = os.getenv("DATABASE_URL", "").strip()
        if database_url:
            return database_url

        db_name = os.getenv("POSTGRES_DB") or os.getenv("DB_BASE", "finam_core")
        db_user = os.getenv("POSTGRES_USER", "finam")
        db_password = os.getenv("POSTGRES_PASSWORD", "")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")

        parts = [
            f"dbname={db_name}",
            f"user={db_user}",
            f"host={db_host}",
            f"port={db_port}",
        ]

        if db_password:
            parts.append(f"password={db_password}")

        return " ".join(parts)

    def save(self, event: TelegramSentimentEvent, symbol: str | None = None) -> int:
        payload: dict[str, Any] = asdict(event)

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ai_sentiment_events
                        (ts, source, symbol, text, label, score, raw_json)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING id
                    """,
                    (
                        event.ts,
                        event.source,
                        symbol,
                        event.text,
                        event.label,
                        float(event.score),
                        json.dumps(payload.get("raw", {}), ensure_ascii=False),
                    ),
                )

                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("PostgreSQL did not return inserted id")

                return int(row[0])

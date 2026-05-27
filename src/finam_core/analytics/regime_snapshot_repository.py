from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class RegimeSnapshot:
    ts: datetime
    symbol: str
    timeframe: str
    regime: str
    volatility_regime: str
    trend_regime: str
    compression_state: str
    intermarket_state: str
    session_type: str
    confidence: float
    source: str
    payload: dict[str, Any]


class RegimeSnapshotRepository:
    """Русский комментарий: сохраняет regime snapshot для research/runtime analytics."""

    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("database_url is required")
        self.database_url = database_url

    def migrate(self) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_regime_snapshots_v2 (
                    id bigserial PRIMARY KEY,
                    ts timestamptz NOT NULL,
                    trade_date date NOT NULL,
                    symbol text NOT NULL,
                    timeframe text NOT NULL,
                    regime text NOT NULL,
                    volatility_regime text NOT NULL,
                    trend_regime text NOT NULL,
                    compression_state text NOT NULL,
                    intermarket_state text NOT NULL,
                    session_type text NOT NULL,
                    confidence double precision NOT NULL DEFAULT 0,
                    source text NOT NULL,
                    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now(),
                    UNIQUE (ts, symbol, timeframe, source)
                );
                """)

                cur.execute("""
                CREATE OR REPLACE VIEW v_regime_snapshots_v2_ru AS
                SELECT
                    trade_date AS "Дата",
                    ts AS "Время",
                    symbol AS "Инструмент",
                    timeframe AS "Таймфрейм",
                    regime AS "Режим",
                    volatility_regime AS "Волатильность",
                    trend_regime AS "Тренд",
                    compression_state AS "Сжатие",
                    intermarket_state AS "Межрыночный режим",
                    session_type AS "Сессия",
                    round(confidence::numeric, 6) AS "Уверенность",
                    source AS "Источник",
                    updated_at AS "Обновлено"
                FROM analytics_regime_snapshots_v2
                ORDER BY ts DESC;
                """)

                cur.execute("""
                CREATE OR REPLACE VIEW v_regime_snapshots_v2_summary_ru AS
                SELECT
                    trade_date AS "Дата",
                    symbol AS "Инструмент",
                    regime AS "Режим",
                    volatility_regime AS "Волатильность",
                    count(*) AS "Снимков",
                    round(avg(confidence)::numeric, 6) AS "Средняя уверенность"
                FROM analytics_regime_snapshots_v2
                GROUP BY trade_date, symbol, regime, volatility_regime
                ORDER BY trade_date DESC, symbol, regime, volatility_regime;
                """)
            conn.commit()

    def save(self, item: RegimeSnapshot) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO analytics_regime_snapshots_v2 (
                    ts, trade_date, symbol, timeframe,
                    regime, volatility_regime, trend_regime,
                    compression_state, intermarket_state, session_type,
                    confidence, source, payload
                )
                VALUES (
                    %(ts)s,
                    (%(ts)s AT TIME ZONE 'Europe/Moscow')::date,
                    %(symbol)s,
                    %(timeframe)s,
                    %(regime)s,
                    %(volatility_regime)s,
                    %(trend_regime)s,
                    %(compression_state)s,
                    %(intermarket_state)s,
                    %(session_type)s,
                    %(confidence)s,
                    %(source)s,
                    %(payload)s
                )
                ON CONFLICT (ts, symbol, timeframe, source)
                DO UPDATE SET
                    regime = EXCLUDED.regime,
                    volatility_regime = EXCLUDED.volatility_regime,
                    trend_regime = EXCLUDED.trend_regime,
                    compression_state = EXCLUDED.compression_state,
                    intermarket_state = EXCLUDED.intermarket_state,
                    session_type = EXCLUDED.session_type,
                    confidence = EXCLUDED.confidence,
                    payload = EXCLUDED.payload,
                    updated_at = now()
                """, {
                    "ts": item.ts,
                    "symbol": item.symbol,
                    "timeframe": item.timeframe,
                    "regime": item.regime,
                    "volatility_regime": item.volatility_regime,
                    "trend_regime": item.trend_regime,
                    "compression_state": item.compression_state,
                    "intermarket_state": item.intermarket_state,
                    "session_type": item.session_type,
                    "confidence": item.confidence,
                    "source": item.source,
                    "payload": Jsonb(item.payload),
                })
            conn.commit()

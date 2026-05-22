from __future__ import annotations

import psycopg

from finam_core.analytics.trade_fill_quality_audit import (
    TradeFillQualityDecision,
    TradeFillQualityInput,
    audit_trade_fill_quality,
)


class TradeFillQualityAuditRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS trade_fill_quality_audit (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            trade_source TEXT NOT NULL,
            total_fills INTEGER NOT NULL,
            buy_fills INTEGER NOT NULL,
            sell_fills INTEGER NOT NULL,
            missing_strategy INTEGER NOT NULL,
            missing_timeframe INTEGER NOT NULL,
            backfill_fills INTEGER NOT NULL,
            status TEXT NOT NULL,
            reconstruction_allowed BOOLEAN NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(symbol, trade_source)
        );

        CREATE INDEX IF NOT EXISTS idx_trade_fill_quality_audit_status
        ON trade_fill_quality_audit(status);

        CREATE INDEX IF NOT EXISTS idx_trade_fill_quality_audit_allowed
        ON trade_fill_quality_audit(reconstruction_allowed);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def build(self, *, symbol: str, trade_source: str = "paper") -> TradeFillQualityDecision:
        sql = """
        SELECT
            COUNT(*) AS total_fills,
            SUM(CASE WHEN UPPER(COALESCE(side, '')) = 'BUY' THEN 1 ELSE 0 END) AS buy_fills,
            SUM(CASE WHEN UPPER(COALESCE(side, '')) = 'SELL' THEN 1 ELSE 0 END) AS sell_fills,
            SUM(
                CASE
                    WHEN COALESCE(strategy, payload->>'strategy', '') = '' THEN 1
                    ELSE 0
                END
            ) AS missing_strategy,
            SUM(
                CASE
                    WHEN COALESCE(timeframe, payload->>'timeframe', payload->>'tf', '') = '' THEN 1
                    ELSE 0
                END
            ) AS missing_timeframe,
            SUM(CASE WHEN COALESCE(origin, '') LIKE 'backfill%%' THEN 1 ELSE 0 END) AS backfill_fills
        FROM trades
        WHERE symbol = %s
          AND COALESCE(trade_source, '') = %s
          AND COALESCE(is_invalid, FALSE) = FALSE
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, trade_source))
                row = cur.fetchone()

        item = TradeFillQualityInput(
            symbol=symbol,
            trade_source=trade_source,
            total_fills=int(row[0] or 0),
            buy_fills=int(row[1] or 0),
            sell_fills=int(row[2] or 0),
            missing_strategy=int(row[3] or 0),
            missing_timeframe=int(row[4] or 0),
            backfill_fills=int(row[5] or 0),
        )

        return audit_trade_fill_quality(item)

    def save(self, decision: TradeFillQualityDecision) -> None:
        sql = """
        INSERT INTO trade_fill_quality_audit (
            symbol,
            trade_source,
            total_fills,
            buy_fills,
            sell_fills,
            missing_strategy,
            missing_timeframe,
            backfill_fills,
            status,
            reconstruction_allowed,
            reason
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (symbol, trade_source)
        DO UPDATE SET
            total_fills = EXCLUDED.total_fills,
            buy_fills = EXCLUDED.buy_fills,
            sell_fills = EXCLUDED.sell_fills,
            missing_strategy = EXCLUDED.missing_strategy,
            missing_timeframe = EXCLUDED.missing_timeframe,
            backfill_fills = EXCLUDED.backfill_fills,
            status = EXCLUDED.status,
            reconstruction_allowed = EXCLUDED.reconstruction_allowed,
            reason = EXCLUDED.reason,
            calculated_at = now()
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        decision.symbol,
                        decision.trade_source,
                        decision.total_fills,
                        decision.buy_fills,
                        decision.sell_fills,
                        decision.missing_strategy,
                        decision.missing_timeframe,
                        decision.backfill_fills,
                        decision.status,
                        decision.reconstruction_allowed,
                        decision.reason,
                    ),
                )
            conn.commit()

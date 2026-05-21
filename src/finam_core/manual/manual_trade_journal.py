from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg


@dataclass(frozen=True)
class ManualTradeRecord:
    symbol: str
    display_name: str
    side: str
    qty: float
    entry_price: float
    stop_price: float | None
    take_price: float | None
    source: str
    strategy_reference: str
    confidence: float
    reason: str
    risk_comment: str
    emotion_state: str
    trade_mode: str = "REAL_MANUAL"


class ManualTradeJournal:
    """
    Русский комментарий:
    Журнал ручных сделок.
    Нужен для сравнения: ручное решение vs системный сигнал vs paper-стратегия.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS manual_trade_journal (
            id BIGSERIAL PRIMARY KEY,
            ts TIMESTAMPTZ NOT NULL DEFAULT now(),
            symbol TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            side TEXT NOT NULL,
            qty NUMERIC NOT NULL,
            entry_price NUMERIC NOT NULL,
            stop_price NUMERIC,
            take_price NUMERIC,
            source TEXT NOT NULL,
            strategy_reference TEXT NOT NULL DEFAULT '',
            confidence NUMERIC NOT NULL DEFAULT 0,
            reason TEXT NOT NULL DEFAULT '',
            risk_comment TEXT NOT NULL DEFAULT '',
            emotion_state TEXT NOT NULL DEFAULT '',
            trade_mode TEXT NOT NULL DEFAULT 'REAL_MANUAL',
            exit_price NUMERIC,
            result_pnl NUMERIC,
            result_r NUMERIC,
            review TEXT NOT NULL DEFAULT '',
            closed_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS idx_manual_trade_journal_ts
        ON manual_trade_journal(ts DESC);

        CREATE INDEX IF NOT EXISTS idx_manual_trade_journal_symbol
        ON manual_trade_journal(symbol, ts DESC);

        CREATE INDEX IF NOT EXISTS idx_manual_trade_journal_source
        ON manual_trade_journal(source, strategy_reference);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def log_entry(self, record: ManualTradeRecord) -> int:
        sql = """
        INSERT INTO manual_trade_journal (
            symbol,
            display_name,
            side,
            qty,
            entry_price,
            stop_price,
            take_price,
            source,
            strategy_reference,
            confidence,
            reason,
            risk_comment,
            emotion_state,
            trade_mode
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        record.symbol,
                        record.display_name,
                        record.side.upper(),
                        record.qty,
                        record.entry_price,
                        record.stop_price,
                        record.take_price,
                        record.source,
                        record.strategy_reference,
                        record.confidence,
                        record.reason,
                        record.risk_comment,
                        record.emotion_state,
                        record.trade_mode,
                    ),
                )
                row = cur.fetchone()
            conn.commit()

        return int(row[0])

    def close_trade(
        self,
        *,
        trade_id: int,
        exit_price: float,
        result_pnl: float,
        result_r: float,
        review: str,
    ) -> None:
        sql = """
        UPDATE manual_trade_journal
        SET
            exit_price = %s,
            result_pnl = %s,
            result_r = %s,
            review = %s,
            closed_at = %s
        WHERE id = %s
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        exit_price,
                        result_pnl,
                        result_r,
                        review,
                        datetime.now(timezone.utc),
                        trade_id,
                    ),
                )
            conn.commit()

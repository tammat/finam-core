from __future__ import annotations

from dataclasses import dataclass

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class SourceWatermark:
    maximum_trade_id: int
    trade_count: int


class ResearchSymbolCheckpoint:
    """Advance a symbol checkpoint only after its complete research chain succeeds."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics.research_symbol_checkpoint_v1 (
                    symbol TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    maximum_trade_id BIGINT NOT NULL DEFAULT 0,
                    trade_count BIGINT NOT NULL DEFAULT 0,
                    last_success_run_id BIGINT,
                    last_success_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (symbol, trade_source)
                )
                """
            )
            conn.commit()

    def watermark(self, symbol: str, trade_source: str) -> SourceWatermark:
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(MAX(id), 0), COUNT(*)
                FROM closed_trade_chains_v2
                WHERE symbol=%s AND COALESCE(trade_source, 'paper')=%s
                """,
                (symbol, trade_source),
            )
            row = cur.fetchone()
        return SourceWatermark(int(row[0]), int(row[1]))

    def is_current(self, symbol: str, trade_source: str, watermark: SourceWatermark) -> bool:
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT maximum_trade_id, trade_count
                FROM analytics.research_symbol_checkpoint_v1
                WHERE symbol=%s AND trade_source=%s
                """,
                (symbol, trade_source),
            )
            row = cur.fetchone()
        return row is not None and (int(row[0]), int(row[1])) == (
            watermark.maximum_trade_id,
            watermark.trade_count,
        )

    def advance(
        self,
        symbol: str,
        trade_source: str,
        watermark: SourceWatermark,
        run_id: int | None,
    ) -> None:
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analytics.research_symbol_checkpoint_v1 (
                    symbol, trade_source, maximum_trade_id, trade_count,
                    last_success_run_id, last_success_at
                ) VALUES (%s,%s,%s,%s,%s,now())
                ON CONFLICT (symbol, trade_source) DO UPDATE SET
                    maximum_trade_id=EXCLUDED.maximum_trade_id,
                    trade_count=EXCLUDED.trade_count,
                    last_success_run_id=EXCLUDED.last_success_run_id,
                    last_success_at=now()
                """,
                (symbol, trade_source, watermark.maximum_trade_id, watermark.trade_count, run_id),
            )
            conn.commit()

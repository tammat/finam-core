from __future__ import annotations

from dataclasses import dataclass

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class SourceWatermark:
    maximum_trade_id: int
    trade_count: int
    maximum_governance_event_id: int
    identity_digest: str


ALGORITHM_VERSION = "RESEARCH_CHECKPOINT_V2_CONTEXT_LINEAGE"


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
                    maximum_governance_event_id BIGINT NOT NULL DEFAULT 0,
                    identity_digest TEXT NOT NULL DEFAULT '',
                    algorithm_version TEXT NOT NULL DEFAULT '',
                    last_success_run_id BIGINT,
                    last_success_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (symbol, trade_source)
                )
                ;
                ALTER TABLE analytics.research_symbol_checkpoint_v1
                    ADD COLUMN IF NOT EXISTS maximum_governance_event_id BIGINT NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS identity_digest TEXT NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS algorithm_version TEXT NOT NULL DEFAULT ''
                """
            )
            conn.commit()

    def watermark(self, symbol: str, trade_source: str) -> SourceWatermark:
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COALESCE((SELECT MAX(id) FROM closed_trade_chains_v2
                              WHERE symbol=%s AND COALESCE(trade_source,'paper')=%s),0),
                    (SELECT COUNT(*) FROM closed_trade_chains_v2
                     WHERE symbol=%s AND COALESCE(trade_source,'paper')=%s),
                    COALESCE((SELECT MAX(g.id) FROM portfolio_governance_events g
                              WHERE g.symbol=%s AND g.created_at <= COALESCE(
                                  (SELECT MAX(c.exit_ts) FROM closed_trade_chains_v2 c
                                   WHERE c.symbol=%s AND COALESCE(c.trade_source,'paper')=%s),
                                  '-infinity'::timestamptz)),0),
                    COALESCE((SELECT md5(string_agg(
                        concat_ws('|',id,strategy,timeframe,trade_source,pnl,entry_ts,exit_ts),
                        ',' ORDER BY id)) FROM closed_trade_chains_v2
                        WHERE symbol=%s AND COALESCE(trade_source,'paper')=%s),'')
                """,
                (symbol, trade_source, symbol, trade_source,
                 symbol, symbol, trade_source, symbol, trade_source),
            )
            row = cur.fetchone()
        return SourceWatermark(int(row[0]), int(row[1]), int(row[2]), str(row[3]))

    def is_current(self, symbol: str, trade_source: str, watermark: SourceWatermark) -> bool:
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT maximum_trade_id, trade_count, maximum_governance_event_id,
                       identity_digest, algorithm_version
                FROM analytics.research_symbol_checkpoint_v1
                WHERE symbol=%s AND trade_source=%s
                """,
                (symbol, trade_source),
            )
            row = cur.fetchone()
        return row is not None and tuple(int(value) for value in row[:3]) == (
            watermark.maximum_trade_id,
            watermark.trade_count,
            watermark.maximum_governance_event_id,
        ) and str(row[3]) == watermark.identity_digest and str(row[4]) == ALGORITHM_VERSION

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
                    maximum_governance_event_id, identity_digest, algorithm_version,
                    last_success_run_id, last_success_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now())
                ON CONFLICT (symbol, trade_source) DO UPDATE SET
                    maximum_trade_id=EXCLUDED.maximum_trade_id,
                    trade_count=EXCLUDED.trade_count,
                    maximum_governance_event_id=EXCLUDED.maximum_governance_event_id,
                    identity_digest=EXCLUDED.identity_digest,
                    algorithm_version=EXCLUDED.algorithm_version,
                    last_success_run_id=EXCLUDED.last_success_run_id,
                    last_success_at=now()
                """,
                (symbol, trade_source, watermark.maximum_trade_id, watermark.trade_count,
                 watermark.maximum_governance_event_id, watermark.identity_digest,
                 ALGORITHM_VERSION, run_id),
            )
            conn.commit()

from __future__ import annotations

import psycopg

from finam_core.analytics.closed_trade_reconstruction_v2 import (
    ClosedTradeChainV2,
    TradeFillV2,
    reconstruct_closed_trades_v2,
)


class ClosedTradeReconstructionV2Repository:
    """
    Русский комментарий:
    Repository для восстановления closed trades v2 из trades.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS closed_trade_chains_v2 (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL DEFAULT '',
            timeframe TEXT NOT NULL DEFAULT '',
            trade_source TEXT NOT NULL DEFAULT '',
            entry_trade_id BIGINT NOT NULL,
            exit_trade_id BIGINT NOT NULL,
            entry_ts TIMESTAMPTZ NOT NULL,
            exit_ts TIMESTAMPTZ NOT NULL,
            side TEXT NOT NULL,
            qty NUMERIC NOT NULL,
            entry_price NUMERIC NOT NULL,
            exit_price NUMERIC NOT NULL,
            pnl NUMERIC NOT NULL,
            duration_sec NUMERIC NOT NULL,
            entry_fill_id TEXT NOT NULL DEFAULT '',
            exit_fill_id TEXT NOT NULL DEFAULT '',
            attribution_status TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(entry_trade_id, exit_trade_id, qty)
        );

        CREATE INDEX IF NOT EXISTS idx_closed_trade_chains_v2_symbol
        ON closed_trade_chains_v2(symbol, exit_ts DESC);

        CREATE INDEX IF NOT EXISTS idx_closed_trade_chains_v2_strategy
        ON closed_trade_chains_v2(strategy, timeframe, exit_ts DESC);

        CREATE INDEX IF NOT EXISTS idx_closed_trade_chains_v2_source
        ON closed_trade_chains_v2(trade_source, exit_ts DESC);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def load_fills(
        self,
        *,
        symbol: str,
        trade_source: str = "paper",
        limit: int = 5000,
    ) -> list[TradeFillV2]:
        sql = """
        SELECT
            id,
            COALESCE(ts, created_at) AS ts,
            symbol,
            side,
            qty,
            price,
            COALESCE(
                payload->>'strategy',
                CASE
                    WHEN symbol LIKE 'NG%%' THEN 'ng_volatility_breakout'
                    WHEN symbol LIKE 'BR%%' THEN 'br_conservative_breakout'
                    ELSE ''
                END
            ) AS strategy,
            COALESCE(
                payload->>'timeframe',
                payload->>'tf',
                CASE
                    WHEN symbol LIKE 'NG%%' THEN 'M5'
                    WHEN symbol LIKE 'BR%%' THEN 'M5'
                    ELSE ''
                END
            ) AS timeframe,
            COALESCE(trade_source, '') AS trade_source,
            COALESCE(origin, '') AS origin,
            COALESCE(fill_id, '') AS fill_id
        FROM trades
        WHERE symbol = %s
          AND COALESCE(trade_source, '') = %s
          AND COALESCE(origin, '') NOT IN ('backtest', 'replay')
          AND qty IS NOT NULL
          AND price IS NOT NULL
          AND side IS NOT NULL
        ORDER BY COALESCE(ts, created_at), id
        LIMIT %s
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, trade_source, limit))
                rows = cur.fetchall()

        return [
            TradeFillV2(
                trade_id=int(row[0]),
                ts=row[1],
                symbol=str(row[2]),
                side=str(row[3]),
                qty=float(row[4] or 0.0),
                price=float(row[5] or 0.0),
                strategy=str(row[6] or ""),
                timeframe=str(row[7] or ""),
                trade_source=str(row[8] or ""),
                origin=str(row[9] or ""),
                fill_id=str(row[10] or ""),
            )
            for row in rows
        ]

    def save_closed_trades(self, items: list[ClosedTradeChainV2]) -> int:
        sql = """
        INSERT INTO closed_trade_chains_v2 (
            symbol,
            strategy,
            timeframe,
            trade_source,
            entry_trade_id,
            exit_trade_id,
            entry_ts,
            exit_ts,
            side,
            qty,
            entry_price,
            exit_price,
            pnl,
            duration_sec,
            entry_fill_id,
            exit_fill_id,
            attribution_status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (entry_trade_id, exit_trade_id, qty) DO NOTHING
        """

        inserted = 0

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in items:
                    cur.execute(
                        sql,
                        (
                            item.symbol,
                            item.strategy,
                            item.timeframe,
                            item.trade_source,
                            item.entry_trade_id,
                            item.exit_trade_id,
                            item.entry_ts,
                            item.exit_ts,
                            item.side,
                            item.qty,
                            item.entry_price,
                            item.exit_price,
                            item.pnl,
                            item.duration_sec,
                            item.entry_fill_id,
                            item.exit_fill_id,
                            item.attribution_status,
                        ),
                    )
                    inserted += cur.rowcount
            conn.commit()

        return inserted

    def rebuild_symbol(
        self,
        *,
        symbol: str,
        trade_source: str = "paper",
        limit: int = 5000,
    ) -> tuple[int, int]:
        fills = self.load_fills(
            symbol=symbol,
            trade_source=trade_source,
            limit=limit,
        )
        closed = reconstruct_closed_trades_v2(fills)
        inserted = self.save_closed_trades(closed)
        return len(closed), inserted

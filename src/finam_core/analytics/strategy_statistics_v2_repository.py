from __future__ import annotations

import psycopg

from finam_core.analytics.strategy_statistics_v2 import (
    StrategyStatisticsV2,
    StrategyTradeSampleV2,
    calculate_strategy_statistics_v2,
)


class StrategyStatisticsV2Repository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS strategy_statistics_v2 (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_source TEXT NOT NULL,
            trades INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            winrate NUMERIC NOT NULL,
            gross_profit NUMERIC NOT NULL,
            gross_loss NUMERIC NOT NULL,
            profit_factor NUMERIC NOT NULL,
            expectancy NUMERIC NOT NULL,
            quality_full_ratio NUMERIC NOT NULL,
            quality_partial_ratio NUMERIC NOT NULL,
            risk_context_weak_ratio NUMERIC NOT NULL,
            high_heat_ratio NUMERIC NOT NULL,
            lifecycle_problem_ratio NUMERIC NOT NULL,
            status TEXT NOT NULL,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(symbol, strategy, timeframe, trade_source)
        );

        CREATE INDEX IF NOT EXISTS idx_strategy_statistics_v2_status
        ON strategy_statistics_v2(status);

        CREATE INDEX IF NOT EXISTS idx_strategy_statistics_v2_strategy
        ON strategy_statistics_v2(strategy, timeframe);

        CREATE INDEX IF NOT EXISTS idx_strategy_statistics_v2_symbol
        ON strategy_statistics_v2(symbol);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def build_for_symbol(self, *, symbol: str) -> list[StrategyStatisticsV2]:
        sql = """
        SELECT
            symbol,
            strategy,
            timeframe,
            trade_source,
            pnl,
            attribution_quality,
            heat_status,
            lifecycle_action
        FROM trade_attribution_v2
        WHERE symbol = %s
        ORDER BY strategy, timeframe, trade_source
        """

        grouped: dict[tuple[str, str, str, str], list[StrategyTradeSampleV2]] = {}

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol,))
                for row in cur.fetchall():
                    key = (
                        str(row[0]),
                        str(row[1] or ""),
                        str(row[2] or ""),
                        str(row[3] or ""),
                    )
                    grouped.setdefault(key, []).append(
                        StrategyTradeSampleV2(
                            pnl=float(row[4] or 0.0),
                            attribution_quality=str(row[5] or ""),
                            heat_status=str(row[6] or "unknown"),
                            lifecycle_action=str(row[7] or "NO_ACTION"),
                        )
                    )

        result = []
        for (sym, strategy, timeframe, trade_source), trades in grouped.items():
            result.append(
                calculate_strategy_statistics_v2(
                    symbol=sym,
                    strategy=strategy,
                    timeframe=timeframe,
                    trade_source=trade_source,
                    trades=trades,
                )
            )

        return result

    def save(self, items: list[StrategyStatisticsV2]) -> int:
        sql = """
        INSERT INTO strategy_statistics_v2 (
            symbol, strategy, timeframe, trade_source,
            trades, wins, losses, winrate,
            gross_profit, gross_loss, profit_factor, expectancy,
            quality_full_ratio, quality_partial_ratio,
            risk_context_weak_ratio, high_heat_ratio,
            lifecycle_problem_ratio, status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (symbol, strategy, timeframe, trade_source)
        DO UPDATE SET
            trades = EXCLUDED.trades,
            wins = EXCLUDED.wins,
            losses = EXCLUDED.losses,
            winrate = EXCLUDED.winrate,
            gross_profit = EXCLUDED.gross_profit,
            gross_loss = EXCLUDED.gross_loss,
            profit_factor = EXCLUDED.profit_factor,
            expectancy = EXCLUDED.expectancy,
            quality_full_ratio = EXCLUDED.quality_full_ratio,
            quality_partial_ratio = EXCLUDED.quality_partial_ratio,
            risk_context_weak_ratio = EXCLUDED.risk_context_weak_ratio,
            high_heat_ratio = EXCLUDED.high_heat_ratio,
            lifecycle_problem_ratio = EXCLUDED.lifecycle_problem_ratio,
            status = EXCLUDED.status,
            calculated_at = now()
        """

        saved = 0

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
                            item.trades,
                            item.wins,
                            item.losses,
                            item.winrate,
                            item.gross_profit,
                            item.gross_loss,
                            item.profit_factor,
                            item.expectancy,
                            item.quality_full_ratio,
                            item.quality_partial_ratio,
                            item.risk_context_weak_ratio,
                            item.high_heat_ratio,
                            item.lifecycle_problem_ratio,
                            item.status,
                        ),
                    )
                    saved += cur.rowcount
            conn.commit()

        return saved

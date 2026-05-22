from __future__ import annotations

import psycopg

from finam_core.analytics.strategy_ranking_v2 import (
    StrategyRankingDecisionV2,
    StrategyRankingInputV2,
    calculate_strategy_rank_v2,
)


class StrategyRankingV2Repository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS strategy_ranking_v2 (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_source TEXT NOT NULL,
            score NUMERIC NOT NULL,
            rank_status TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(symbol, strategy, timeframe, trade_source)
        );

        CREATE INDEX IF NOT EXISTS idx_strategy_ranking_v2_score
        ON strategy_ranking_v2(score DESC);

        CREATE INDEX IF NOT EXISTS idx_strategy_ranking_v2_status
        ON strategy_ranking_v2(rank_status);

        CREATE INDEX IF NOT EXISTS idx_strategy_ranking_v2_symbol
        ON strategy_ranking_v2(symbol);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def build(self, *, symbol: str | None = None) -> list[StrategyRankingDecisionV2]:
        where = ""
        params: tuple = ()

        if symbol:
            where = "WHERE symbol = %s"
            params = (symbol,)

        sql = f"""
        SELECT
            symbol,
            strategy,
            timeframe,
            trade_source,
            trades,
            profit_factor,
            winrate,
            expectancy,
            quality_full_ratio,
            risk_context_weak_ratio,
            high_heat_ratio,
            lifecycle_problem_ratio,
            status
        FROM strategy_statistics_v2
        {where}
        """

        items: list[StrategyRankingDecisionV2] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        for row in rows:
            decision = calculate_strategy_rank_v2(
                StrategyRankingInputV2(
                    symbol=str(row[0]),
                    strategy=str(row[1]),
                    timeframe=str(row[2]),
                    trade_source=str(row[3]),
                    trades=int(row[4] or 0),
                    profit_factor=float(row[5] or 0.0),
                    winrate=float(row[6] or 0.0),
                    expectancy=float(row[7] or 0.0),
                    quality_full_ratio=float(row[8] or 0.0),
                    risk_context_weak_ratio=float(row[9] or 0.0),
                    high_heat_ratio=float(row[10] or 0.0),
                    lifecycle_problem_ratio=float(row[11] or 0.0),
                    status=str(row[12] or ""),
                )
            )
            items.append(decision)

        return sorted(items, key=lambda x: x.score, reverse=True)

    def save(self, items: list[StrategyRankingDecisionV2]) -> int:
        sql = """
        INSERT INTO strategy_ranking_v2 (
            symbol,
            strategy,
            timeframe,
            trade_source,
            score,
            rank_status,
            reason
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (symbol, strategy, timeframe, trade_source)
        DO UPDATE SET
            score = EXCLUDED.score,
            rank_status = EXCLUDED.rank_status,
            reason = EXCLUDED.reason,
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
                            item.score,
                            item.rank_status,
                            item.reason,
                        ),
                    )
                    saved += cur.rowcount
            conn.commit()

        return saved

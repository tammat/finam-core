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
            where = "WHERE symbol = %s AND COALESCE(strategy, '') <> '' AND COALESCE(timeframe, '') <> ''"
            params = (symbol,)
        else:
            where = "WHERE COALESCE(strategy, '') <> '' AND COALESCE(timeframe, '') <> ''"

        sql = f"""
        SELECT
            s.symbol,
            s.strategy,
            s.timeframe,
            s.trade_source,
            s.trades,
            s.profit_factor,
            s.winrate,
            s.expectancy,
            s.quality_full_ratio,
            s.risk_context_weak_ratio,
            s.high_heat_ratio,
            s.lifecycle_problem_ratio,
            s.status,
            COALESCE(v.verdict, '') AS research_verdict,
            COALESCE(v.confidence, 0)::float AS research_confidence,
            COALESCE(v.reason, '') AS research_reason
        FROM strategy_statistics_v2 s
        LEFT JOIN strategy_research_verdicts v
          ON v.symbol = s.symbol
         AND v.strategy = s.strategy
         AND v.timeframe = s.timeframe
         AND v.trade_source = s.trade_source
        {where.replace("symbol", "s.symbol").replace("strategy", "s.strategy").replace("timeframe", "s.timeframe")}
          AND COALESCE(s.strategy, '') <> ''
          AND COALESCE(s.timeframe, '') <> ''
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

            research_verdict = str(row[13] or "")
            research_confidence = float(row[14] or 0.0)
            research_reason = str(row[15] or "")

            # Русский комментарий: WATCH_DIVERGENCE не допускает стратегию в runtime,
            # но запрещает терять положительный OOS-сигнал внутри жёсткого REJECT.
            if decision.rank_status == "REJECT" and research_verdict == "WATCH_DIVERGENCE":
                decision = StrategyRankingDecisionV2(
                    symbol=decision.symbol,
                    strategy=decision.strategy,
                    timeframe=decision.timeframe,
                    trade_source=decision.trade_source,
                    score=max(float(decision.score), 35.0),
                    rank_status="WATCH_DIVERGENCE",
                    reason=f"research_verdict:{research_verdict};{research_reason};confidence={round(research_confidence, 4)}",
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

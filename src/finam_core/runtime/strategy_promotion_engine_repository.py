from __future__ import annotations

import psycopg

from finam_core.runtime.strategy_promotion_engine_v1 import (
    StrategyPromotionEngineDecision,
    StrategyPromotionEngineInput,
    decide_strategy_promotion_v1,
)


class StrategyPromotionEngineRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS strategy_promotion_decisions (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_source TEXT NOT NULL,
            decision TEXT NOT NULL,
            target_lifecycle_state TEXT NOT NULL,
            allow_runtime BOOLEAN NOT NULL,
            allow_radar BOOLEAN NOT NULL,
            allow_research BOOLEAN NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(symbol, strategy, timeframe, trade_source)
        );

        CREATE INDEX IF NOT EXISTS idx_strategy_promotion_decisions_decision
        ON strategy_promotion_decisions(decision);

        CREATE INDEX IF NOT EXISTS idx_strategy_promotion_decisions_symbol
        ON strategy_promotion_decisions(symbol);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def build(self, *, symbol: str | None = None) -> list[StrategyPromotionEngineDecision]:
        where = ""
        params = []

        if symbol:
            where = "WHERE s.symbol = %s"
            params.append(symbol)

        sql = f"""
        SELECT
            s.symbol,
            s.strategy,
            s.timeframe,
            s.trade_source,
            s.trades,
            s.profit_factor,
            s.expectancy,
            s.winrate,
            COALESCE(r.score, 0) AS score,
            COALESCE(r.rank_status, '') AS rank_status,
            COALESCE(q.status, 'UNKNOWN') AS fill_quality_status,
            COALESCE(q.reconstruction_allowed, FALSE) AS reconstruction_allowed,
            COALESCE(l.lifecycle_state, 'UNKNOWN') AS lifecycle_state
        FROM strategy_statistics_v2 s
        LEFT JOIN strategy_ranking_v2 r
          ON r.symbol = s.symbol
         AND r.strategy = s.strategy
         AND r.timeframe = s.timeframe
         AND r.trade_source = s.trade_source
        LEFT JOIN trade_fill_quality_audit q
          ON q.symbol = s.symbol
         AND q.trade_source = s.trade_source
        LEFT JOIN strategy_lifecycle_state l
          ON l.symbol = s.symbol
         AND l.strategy = s.strategy
         AND l.timeframe = s.timeframe
        {where}
        ORDER BY s.symbol, r.score DESC
        """

        decisions: list[StrategyPromotionEngineDecision] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()

        for row in rows:
            decisions.append(
                decide_strategy_promotion_v1(
                    StrategyPromotionEngineInput(
                        symbol=str(row[0]),
                        strategy=str(row[1]),
                        timeframe=str(row[2]),
                        trade_source=str(row[3]),
                        trades=int(row[4] or 0),
                        profit_factor=float(row[5] or 0.0),
                        expectancy=float(row[6] or 0.0),
                        winrate=float(row[7] or 0.0),
                        score=float(row[8] or 0.0),
                        rank_status=str(row[9] or ""),
                        fill_quality_status=str(row[10] or "UNKNOWN"),
                        reconstruction_allowed=bool(row[11]),
                        lifecycle_state=str(row[12] or "UNKNOWN"),
                    )
                )
            )

        return decisions

    def save(self, items: list[StrategyPromotionEngineDecision]) -> int:
        sql = """
        INSERT INTO strategy_promotion_decisions (
            symbol,
            strategy,
            timeframe,
            trade_source,
            decision,
            target_lifecycle_state,
            allow_runtime,
            allow_radar,
            allow_research,
            reason,
            decided_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT (symbol, strategy, timeframe, trade_source)
        DO UPDATE SET
            decision = EXCLUDED.decision,
            target_lifecycle_state = EXCLUDED.target_lifecycle_state,
            allow_runtime = EXCLUDED.allow_runtime,
            allow_radar = EXCLUDED.allow_radar,
            allow_research = EXCLUDED.allow_research,
            reason = EXCLUDED.reason,
            decided_at = now()
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
                            item.decision,
                            item.target_lifecycle_state,
                            item.allow_runtime,
                            item.allow_radar,
                            item.allow_research,
                            item.reason,
                        ),
                    )
                    saved += cur.rowcount
            conn.commit()

        return saved

    def apply_to_lifecycle(self, items: list[StrategyPromotionEngineDecision]) -> int:
        """
        Русский комментарий:
        Обновляет strategy_lifecycle_state на основании promotion decision.
        Это всё ещё governance-layer, не execution.
        """

        sql = """
        INSERT INTO strategy_lifecycle_state (
            symbol,
            strategy,
            timeframe,
            lifecycle_state,
            allow_runtime,
            allow_radar,
            allow_research,
            reason,
            updated_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT (symbol, strategy, timeframe)
        DO UPDATE SET
            lifecycle_state = EXCLUDED.lifecycle_state,
            allow_runtime = EXCLUDED.allow_runtime,
            allow_radar = EXCLUDED.allow_radar,
            allow_research = EXCLUDED.allow_research,
            reason = EXCLUDED.reason,
            updated_at = now()
        """

        applied = 0

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in items:
                    cur.execute(
                        sql,
                        (
                            item.symbol,
                            item.strategy,
                            item.timeframe,
                            item.target_lifecycle_state,
                            item.allow_runtime,
                            item.allow_radar,
                            item.allow_research,
                            item.reason,
                        ),
                    )
                    applied += cur.rowcount
            conn.commit()

        return applied

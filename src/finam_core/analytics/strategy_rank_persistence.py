from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from finam_core.analytics.strategy_ranker import (
    StrategyRankDecision,
    StrategyRanker,
    StrategyScorecardRow,
)


class StrategyRankPersistence:
    """Русский комментарий: считает решения StrategyRanker и сохраняет их в PostgreSQL."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger
        self.ranker = StrategyRanker()

    def calculate_and_save_daily(self, trade_date: date) -> int:
        rows = self._load_scorecard_rows(trade_date)
        saved = 0

        for row in rows:
            decision = self.ranker.rank(row)
            self._save_decision(trade_date, decision)
            saved += 1

        return saved

    def _load_scorecard_rows(self, trade_date: date) -> list[StrategyScorecardRow]:
        sql = """
        select
            strategy,
            symbol,
            timeframe,
            trades,
            net_pnl,
            winrate,
            profit_factor,
            expectancy
        from strategy_scorecard_daily
        where trade_date = %s
        order by net_pnl desc
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trade_date,))
                rows = cur.fetchall()

        return [
            StrategyScorecardRow(
                strategy=str(row[0]),
                symbol=str(row[1]),
                timeframe=str(row[2]),
                trades=int(row[3]),
                net_pnl=Decimal(str(row[4])),
                winrate=Decimal(str(row[5])),
                profit_factor=Decimal(str(row[6])),
                expectancy=Decimal(str(row[7])),
            )
            for row in rows
        ]

    def _save_decision(self, trade_date: date, decision: StrategyRankDecision) -> None:
        sql = """
        insert into strategy_rank_decisions (
            trade_date,
            strategy,
            symbol,
            timeframe,
            decision,
            score,
            reason
        )
        values (%s, %s, %s, %s, %s, %s, %s)
        on conflict (trade_date, strategy, symbol, timeframe)
        do update set
            decision = excluded.decision,
            score = excluded.score,
            reason = excluded.reason
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        trade_date,
                        decision.strategy,
                        decision.symbol,
                        decision.timeframe,
                        decision.decision,
                        decision.score,
                        decision.reason,
                    ),
                )
            conn.commit()

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from finam_core.analytics.strategy_scorecard import (
    StrategyScorecardCalculator,
    TradeResult,
)


class StrategyScorecardPersistence:
    """Русский комментарий: считает scorecard по closed_trades и пишет результат в PostgreSQL."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger
        self.calculator = StrategyScorecardCalculator()

    def calculate_and_save_daily(self, trade_date: date) -> int:
        rows = self._load_closed_trades(trade_date)
        grouped: dict[tuple[str, str, str], list[TradeResult]] = {}

        for row in rows:
            symbol, strategy, timeframe, net_pnl, commission = row

            key = (
                str(symbol),
                str(strategy or "unknown"),
                str(timeframe or "unknown"),
            )

            grouped.setdefault(key, []).append(
                TradeResult(
                    symbol=key[0],
                    strategy=key[1],
                    timeframe=key[2],
                    pnl=Decimal(str(net_pnl or 0)),
                    commission=Decimal(str(commission or 0)),
                    r_multiple=Decimal("0"),
                )
            )

        saved = 0

        for trades in grouped.values():
            score = self.calculator.calculate(trades)
            self._save_scorecard(trade_date, score)
            saved += 1

        return saved

    def _load_closed_trades(self, trade_date: date) -> list[tuple]:
        sql = """
        select
            symbol,
            coalesce(strategy, 'unknown') as strategy,
            coalesce(horizon, 'unknown') as timeframe,
            net_pnl,
            commission
        from closed_trades
        where created_at::date = %s
          and trade_source = 'paper'
          and coalesce(strategy, payload->>'strategy', '') <> ''
          and coalesce(strategy, payload->>'strategy', '') <> 'unknown'
        order by symbol, strategy, horizon, created_at
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trade_date,))
                return list(cur.fetchall())

    def _save_scorecard(self, trade_date: date, score) -> None:
        sql = """
        insert into strategy_scorecard_daily (
            trade_date,
            strategy,
            symbol,
            timeframe,
            trades,
            gross_pnl,
            net_pnl,
            winrate,
            profit_factor,
            avg_win,
            avg_loss,
            expectancy,
            max_drawdown,
            avg_r,
            commission_total
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (trade_date, strategy, symbol, timeframe)
        do update set
            trades = excluded.trades,
            gross_pnl = excluded.gross_pnl,
            net_pnl = excluded.net_pnl,
            winrate = excluded.winrate,
            profit_factor = excluded.profit_factor,
            avg_win = excluded.avg_win,
            avg_loss = excluded.avg_loss,
            expectancy = excluded.expectancy,
            max_drawdown = excluded.max_drawdown,
            avg_r = excluded.avg_r,
            commission_total = excluded.commission_total
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        trade_date,
                        score.strategy,
                        score.symbol,
                        score.timeframe,
                        score.trades,
                        score.gross_pnl,
                        score.net_pnl,
                        score.winrate,
                        score.profit_factor,
                        score.avg_win,
                        score.avg_loss,
                        score.expectancy,
                        score.max_drawdown,
                        score.avg_r,
                        score.commission_total,
                    ),
                )
            conn.commit()

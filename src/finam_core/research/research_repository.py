from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class TradeSample:
    """Сделка для research-аналитики."""

    strategy: str
    symbol: str
    regime: str
    pnl: float


class ResearchRepository:
    """Русский комментарий: чтение сделок и запись research-результатов в PostgreSQL."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ["DATABASE_URL"]

    def load_trade_samples(self) -> list[TradeSample]:
        sql = """
        SELECT
            COALESCE(NULLIF(strategy, ''), 'unknown') AS strategy,
            COALESCE(NULLIF(symbol, ''), 'unknown') AS symbol,
            COALESCE(NULLIF(payload->>'regime', ''), 'unknown') AS regime,
            COALESCE(
                NULLIF(payload->>'realized_pnl', '')::float,
                NULLIF(payload->>'pnl', '')::float,
                NULLIF(payload->>'net_pnl', '')::float,
                0.0
            ) AS pnl
        FROM trades
        WHERE COALESCE(is_invalid, false) = false
          AND strategy IS NOT NULL
          AND strategy <> ''
          AND payload ?| ARRAY['realized_pnl', 'pnl', 'net_pnl']
        ORDER BY created_at ASC, id ASC;
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()

        return [
            TradeSample(
                strategy=str(row[0]),
                symbol=str(row[1]),
                regime=str(row[2]),
                pnl=float(row[3]),
            )
            for row in rows
        ]

    def save_research_result(
        self,
        *,
        run_id: str,
        strategy: str,
        symbol: str,
        regime: str,
        metrics,
        decision: str,
        reason: str,
    ) -> None:
        sql = """
        INSERT INTO strategy_research_results (
            run_id,
            strategy,
            symbol,
            regime,
            trades,
            wins,
            losses,
            total_pnl,
            avg_pnl,
            win_rate,
            profit_factor,
            expectancy,
            max_drawdown,
            decision,
            reason
        )
        VALUES (
            %(run_id)s,
            %(strategy)s,
            %(symbol)s,
            %(regime)s,
            %(trades)s,
            %(wins)s,
            %(losses)s,
            %(total_pnl)s,
            %(avg_pnl)s,
            %(win_rate)s,
            %(profit_factor)s,
            %(expectancy)s,
            %(max_drawdown)s,
            %(decision)s,
            %(reason)s
        );
        """

        params = {
            "run_id": run_id,
            "strategy": strategy,
            "symbol": symbol,
            "regime": regime,
            "trades": metrics.trades,
            "wins": metrics.wins,
            "losses": metrics.losses,
            "total_pnl": metrics.total_pnl,
            "avg_pnl": metrics.avg_pnl,
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
            "expectancy": metrics.expectancy,
            "max_drawdown": metrics.max_drawdown,
            "decision": decision,
            "reason": reason,
        }

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()

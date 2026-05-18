from __future__ import annotations

import argparse

from finam_core.portfolio.portfolio_allocator import (
    PortfolioAllocator,
    StrategyAllocationInput,
)
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--trade-date", required=True)
    p.add_argument("--max-strategy-weight", type=float, default=0.35)
    p.add_argument("--max-symbol-weight", type=float, default=0.40)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    sql = """
    select
        strategy,
        symbol,
        net_pnl,
        expectancy,
        winrate,
        profit_factor,
        max_drawdown
    from strategy_scorecard_daily
    where trade_date = %s
      and strategy <> 'unknown'
    order by net_pnl desc
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.trade_date,))
            rows = cur.fetchall()

    if not rows:
        print(f"РАСПРЕДЕЛЕНИЕ_КАПИТАЛА_ПУСТО дата={args.trade_date}", flush=True)
        return 0

    items: list[StrategyAllocationInput] = []

    for row in rows:
        strategy = str(row[0])
        symbol = str(row[1])
        expectancy = float(row[3] or 0.0)
        winrate = float(row[4] or 0.0)
        max_drawdown = float(row[6] or 0.0)

        # Русский комментарий: временная v1-оценка grade без bootstrap.
        if expectancy > 0 and winrate >= 0.60:
            grade = "A"
            p_positive = 0.90
            stability_score = 45.0
        elif expectancy > 0:
            grade = "B"
            p_positive = 0.80
            stability_score = 30.0
        elif expectancy > -0.05:
            grade = "C"
            p_positive = 0.70
            stability_score = 15.0
        else:
            grade = "D"
            p_positive = 0.50
            stability_score = 0.0

        items.append(
            StrategyAllocationInput(
                strategy=strategy,
                symbol=symbol,
                grade=grade,
                stability_score=stability_score,
                p_positive=p_positive,
                max_drawdown=max_drawdown,
            )
        )

    allocations = PortfolioAllocator().allocate(
        items,
        max_strategy_weight=args.max_strategy_weight,
        max_symbol_weight=args.max_symbol_weight,
    )

    for allocation in allocations:
        print(
            "РАСПРЕДЕЛЕНИЕ_КАПИТАЛА "
            f"дата={args.trade_date} "
            f"инструмент={allocation.symbol} "
            f"стратегия={allocation.strategy} "
            f"вес_капитала={allocation.capital_weight:.6f} "
            f"множитель_риска={allocation.risk_multiplier:.6f} "
            f"решение={allocation.decision} "
            f"причина={allocation.reason}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

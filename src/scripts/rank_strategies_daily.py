from __future__ import annotations

import argparse
from decimal import Decimal

from finam_core.analytics.strategy_ranker import (
    StrategyRankDecision,
    StrategyRanker,
    StrategyScorecardRow,
)
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Дата scorecard YYYY-MM-DD")
    return parser.parse_args()


def load_rows(pg, trade_date: str) -> list[StrategyScorecardRow]:
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

    with pg._connect() as conn:
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


def print_decision(decision: StrategyRankDecision) -> None:
    print(
        f"{decision.decision:<8} "
        f"strategy={decision.strategy:<32} "
        f"symbol={decision.symbol:<16} "
        f"timeframe={decision.timeframe:<12} "
        f"score={round(decision.score, 4)} "
        f"reason={decision.reason}",
        flush=True,
    )


def main() -> int:
    args = parse_args()

    rows = load_rows(PostgresLogger(), args.date)
    ranker = StrategyRanker()

    for row in rows:
        print_decision(ranker.rank(row))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

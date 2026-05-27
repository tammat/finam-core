from __future__ import annotations

import argparse
import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.edge_validation_engine import EdgeValidationEngine
from finam_core.analytics.statistics_repository import build_psycopg_url


def load_pnls(symbol: str, trade_date: str | None) -> list[float]:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    where = ["symbol = %s"]
    params: list[object] = [symbol]

    if trade_date:
        where.append("trade_date = %s")
        params.append(trade_date)

    sql = f"""
        select trade_pnl
        from analytics_intraday_pnl
        where {' and '.join(where)}
        order by ts
    """

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [float(row["trade_pnl"]) for row in cur.fetchall()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", default="")
    parser.add_argument("--timeframe", default="")
    parser.add_argument("--date", default=None)
    parser.add_argument("--min-trades", type=int, default=30)
    args = parser.parse_args()

    pnls = load_pnls(symbol=args.symbol, trade_date=args.date)

    result = EdgeValidationEngine().validate(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        pnls=pnls,
        min_trades=args.min_trades,
    )

    print("EDGE_VALIDATION_REPORT_V1")
    print(f"symbol={result.symbol}")
    print(f"strategy={result.strategy}")
    print(f"timeframe={result.timeframe}")
    print(f"trades={result.trades}")
    print(f"pnl={result.pnl:.6f}")
    print(f"wins={result.wins}")
    print(f"losses={result.losses}")
    print(f"winrate={result.winrate:.6f}")
    print(f"profit_factor={result.profit_factor:.6f}")
    print(f"expectancy={result.expectancy:.6f}")
    print(f"status={result.status}")
    print(f"reason={result.reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

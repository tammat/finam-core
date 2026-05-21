from __future__ import annotations

import argparse

from finam_core.analytics.trade_statistics import (
    calculate_trade_statistics,
)

from finam_core.analytics.statistics_repository import (
    StatisticsRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument(
        "--fallback-commission-rate",
        type=float,
        default=0.0,
        help="Fallback commission rate, e.g. 0.0001 means 0.01 percent of turnover",
    )

    args = parser.parse_args()

    repo = StatisticsRepository()

    if args.migrate:
        repo.migrate()

    trades = repo.load_closed_trades(
        symbol=args.symbol,
        fallback_commission_rate=args.fallback_commission_rate,
    )

    stats = calculate_trade_statistics(
        symbol=args.symbol,
        trades=trades,
    )

    repo.save_statistics(
        stats=stats,
        timeframe=args.timeframe,
        strategy=args.strategy,
    )

    print(
        "ANALYTICS_BUILD_OK "
        f"symbol={stats.symbol} "
        f"trades={stats.trades} "
        f"winrate={stats.winrate} "
        f"net_pnl={stats.net_pnl} "
        f"profit_factor={stats.profit_factor}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

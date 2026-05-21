from __future__ import annotations

import argparse

from finam_core.analytics.equity_curve import (
    build_equity_curve,
)

from finam_core.analytics.statistics_repository import (
    StatisticsRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)

    args = parser.parse_args()

    repo = StatisticsRepository()

    repo.migrate_equity_curve()

    trades = repo.load_closed_trades(
        symbol=args.symbol,
    )

    points = build_equity_curve(
        [t.pnl for t in trades]
    )

    repo.save_equity_curve(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        points=points,
    )

    if points:
        final_equity = points[-1].cumulative_pnl
        max_drawdown = min(p.drawdown for p in points)
    else:
        final_equity = 0.0
        max_drawdown = 0.0

    print(
        "ANALYTICS_EQUITY_CURVE_OK "
        f"symbol={args.symbol} "
        f"points={len(points)} "
        f"final_equity={round(final_equity, 4)} "
        f"max_drawdown={round(max_drawdown, 4)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

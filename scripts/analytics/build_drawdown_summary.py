from __future__ import annotations

import argparse

from finam_core.analytics.drawdown_summary import build_drawdown_summary
from finam_core.analytics.statistics_repository import StatisticsRepository


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument(
        "--fallback-commission-rate",
        type=float,
        default=0.0,
    )
    parser.add_argument("--migrate", action="store_true")

    args = parser.parse_args()

    repo = StatisticsRepository()

    if args.migrate:
        repo.migrate_drawdown_summary()

    trades = repo.load_closed_trades(
        symbol=args.symbol,
        fallback_commission_rate=args.fallback_commission_rate,
    )

    summary = build_drawdown_summary([trade.pnl for trade in trades])

    repo.save_drawdown_summary(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        summary=summary,
    )

    print(
        "ANALYTICS_DRAWDOWN_SUMMARY_OK "
        f"symbol={args.symbol} "
        f"trades={summary.trades} "
        f"final_pnl={summary.final_pnl} "
        f"max_drawdown={summary.max_drawdown} "
        f"max_drawdown_trade_index={summary.max_drawdown_trade_index} "
        f"max_win_streak={summary.max_win_streak} "
        f"max_loss_streak={summary.max_loss_streak} "
        f"payoff_ratio={summary.payoff_ratio}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

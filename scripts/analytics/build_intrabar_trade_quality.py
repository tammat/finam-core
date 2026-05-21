from __future__ import annotations

import argparse

from finam_core.analytics.intrabar_repository import IntrabarAnalyticsRepository


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--migrate", action="store_true")

    args = parser.parse_args()

    repo = IntrabarAnalyticsRepository()

    if args.migrate:
        repo.migrate_intrabar_trade_quality()

    qualities = repo.build_intrabar_quality(
        symbol=args.symbol,
        timeframe=args.timeframe,
    )

    repo.save_intrabar_quality(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        qualities=qualities,
    )

    avg_efficiency = (
        sum(item.exit_efficiency for item in qualities) / len(qualities)
        if qualities else 0.0
    )

    avg_mfe = (
        sum(item.mfe for item in qualities) / len(qualities)
        if qualities else 0.0
    )

    avg_mae = (
        sum(item.mae for item in qualities) / len(qualities)
        if qualities else 0.0
    )

    print(
        "ANALYTICS_INTRABAR_TRADE_QUALITY_OK "
        f"symbol={args.symbol} "
        f"trades={len(qualities)} "
        f"avg_mfe={round(avg_mfe, 4)} "
        f"avg_mae={round(avg_mae, 4)} "
        f"avg_exit_efficiency={round(avg_efficiency, 4)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

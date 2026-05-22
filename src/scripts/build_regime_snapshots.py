from __future__ import annotations

import argparse

from finam_core.analytics.regime_snapshot_repository import RegimeSnapshotRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--regime", default="unknown")
    parser.add_argument("--trend", default="unknown")
    parser.add_argument("--volatility", default="unknown")
    parser.add_argument("--atr", type=float, default=0.0)
    parser.add_argument("--source", default="manual")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    repo = RegimeSnapshotRepository()

    if args.migrate or args.save:
        repo.migrate()

    if args.save:
        repo.save_snapshot(
            symbol=args.symbol,
            timeframe=args.timeframe,
            regime=args.regime,
            trend=args.trend,
            volatility=args.volatility,
            atr=args.atr,
            source=args.source,
        )

    print(
        "REGIME_SNAPSHOT_OK "
        f"symbol={args.symbol} timeframe={args.timeframe} "
        f"regime={args.regime} trend={args.trend} volatility={args.volatility}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

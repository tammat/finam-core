from __future__ import annotations

import argparse

from finam_core.analytics.trade_quality import (
    calculate_trade_quality,
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

    repo.migrate_trade_quality()

    trades = repo.load_closed_trades(
        symbol=args.symbol,
    )

    pnls = [t.pnl for t in trades]

    """
    Временный approximation layer.

    Пока нет intrabar MAE/MFE reconstruction,
    используем:
    - mfe = max(pnl, 0)
    - mae = min(pnl, 0)

    Это baseline analytics layer v1.
    """

    mfes = [max(p, 0) for p in pnls]
    maes = [min(p, 0) for p in pnls]

    qualities = calculate_trade_quality(
        pnls=pnls,
        mfes=mfes,
        maes=maes,
    )

    repo.save_trade_quality(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        qualities=qualities,
    )

    avg_efficiency = (
        sum(x.efficiency for x in qualities) / len(qualities)
        if qualities else 0.0
    )

    print(
        "ANALYTICS_TRADE_QUALITY_OK "
        f"symbol={args.symbol} "
        f"trades={len(qualities)} "
        f"avg_efficiency={round(avg_efficiency, 4)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

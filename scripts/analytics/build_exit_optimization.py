from __future__ import annotations

import argparse

from finam_core.analytics.exit_optimization_repository import (
    ExitOptimizationRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--migrate", action="store_true")

    args = parser.parse_args()

    repo = ExitOptimizationRepository()

    if args.migrate:
        repo.migrate_exit_optimization()

    profile = repo.build_profile(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
    )

    repo.save_profile(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        profile=profile,
    )

    print(
        "ANALYTICS_EXIT_OPTIMIZATION_OK "
        f"symbol={args.symbol} "
        f"strategy={args.strategy} "
        f"timeframe={args.timeframe} "
        f"trades={profile.trades} "
        f"avg_pnl={profile.avg_pnl} "
        f"avg_exit_efficiency={profile.avg_exit_efficiency} "
        f"take50={profile.recommended_take_50} "
        f"take70={profile.recommended_take_70} "
        f"take80={profile.recommended_take_80} "
        f"stop50={profile.recommended_stop_50} "
        f"stop70={profile.recommended_stop_70} "
        f"stop80={profile.recommended_stop_80}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
